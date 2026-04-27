import os
import uuid
import traceback
import bcrypt

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any

from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime

from app.engine.master_engine import run_full_analysis
from app.chat import ask_ai, save_message, get_chat_history

# =========================
# LOAD ENV
# =========================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing Supabase environment variables")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# AUTH
# =========================
def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")

    token = authorization.replace("Bearer ", "")

    res = supabase.table("sessions") \
        .select("*") \
        .eq("token", token) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="Invalid token")

    return res.data[0]["user_id"]

# =========================
# APP INIT
# =========================
app = FastAPI(title="Clarion Digital Twin API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# MODELS
# =========================
class AnalysisRequest(BaseModel):
    data: Dict[str, Any]

class LoginRequest(BaseModel):
    email: str
    password: str

class CreateUserRequest(BaseModel):
    email: str
    password: str

class SubmitRequest(BaseModel):
    answers: Dict[str, Any]

class ChatRequest(BaseModel):
    chat_id: int | None = None
    message: str

# =========================
# ROOT
# =========================
@app.get("/")
def root():
    return {"status": "running"}

# =========================
# ANALYSIS
# =========================
@app.post("/analyze")
def analyze(request: AnalysisRequest, user: str = Depends(get_current_user)):
    try:
        result = run_full_analysis(request.data)
        return {"success": True, "result": result}
    except Exception as e:
        return {"success": False, "error": str(e)}

# =========================
# CREATE USER
# =========================
@app.post("/create-user")
def create_user(request: CreateUserRequest, x_admin_key: str = Header(None)):

    if x_admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    existing = supabase.table("users") \
        .select("*") \
        .eq("email", request.email) \
        .execute()

    if existing.data:
        raise HTTPException(status_code=400, detail="User exists")

    hashed_pw = bcrypt.hashpw(
        request.password.encode(),
        bcrypt.gensalt()
    ).decode()

    result = supabase.table("users").insert({
        "email": request.email,
        "password": hashed_pw
    }).execute()

    return {"success": True, "user": result.data[0]}

# =========================
# LOGIN
# =========================
@app.post("/login")
def login(request: LoginRequest):

    res = supabase.table("users") \
        .select("*") \
        .eq("email", request.email) \
        .execute()

    if not res.data:
        raise HTTPException(status_code=401, detail="User not found")

    user = res.data[0]

    if not bcrypt.checkpw(
        request.password.encode(),
        user["password"].encode()
    ):
        raise HTTPException(status_code=401, detail="Wrong password")

    token = str(uuid.uuid4())

    supabase.table("sessions").insert({
        "user_id": user["id"],
        "token": token
    }).execute()

    return {
        "success": True,
        "token": token,
        "user_id": user["id"]
    }

# =========================
# SUBMIT ANSWERS
# =========================
@app.post("/submit")
def submit_answers(request: SubmitRequest, user_id: str = Depends(get_current_user)):

    rows = []
    for qid, ans in request.answers.items():
        rows.append({
            "user_id": user_id,
            "question_id": qid,
            "answer": ans,
            "updated_at": datetime.utcnow().isoformat()
        })

    res = supabase.table("answers").upsert(
        rows,
        on_conflict="user_id,question_id"
    ).execute()

    return {"success": True, "saved": res.data}

# =========================
# CHAT (UPDATED 🔥)
# =========================
@app.post("/chat/message")
def chat(req: ChatRequest, user_id: str = Depends(get_current_user)):

    # Create chat if needed
    if not req.chat_id:
        chat = supabase.table("chats").insert({
            "title": "New Chat",
            "user_id": user_id
        }).execute()

        chat_id = chat.data[0]["id"]
    else:
        chat_id = req.chat_id

    # Save user message
    save_message(chat_id, "user", req.message)

    # Get history
    history = get_chat_history(chat_id)

    # AI response (WITH USER CONTEXT 🔥)
    answer = ask_ai(req.message, history, user_id)

    # Save AI message
    save_message(chat_id, "assistant", answer)

    return {
        "chat_id": chat_id,
        "answer": answer
    }

# =========================
# GET CHATS
# =========================
@app.get("/chats")
def get_chats(user_id: str = Depends(get_current_user)):
    res = supabase.table("chats") \
        .select("*") \
        .eq("user_id", user_id) \
        .execute()

    return res.data

# =========================
# GET MESSAGES
# =========================
@app.get("/chats/{chat_id}")
def get_messages(chat_id: int, user_id: str = Depends(get_current_user)):

    res = supabase.table("messages") \
        .select("*") \
        .eq("chat_id", chat_id) \
        .order("id") \
        .execute()

    return res.data