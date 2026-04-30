import os
import uuid
import traceback
import bcrypt

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from dotenv import load_dotenv
from supabase import create_client

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

print("✅ Supabase connected:", SUPABASE_URL)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# AUTH SYSTEM
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
app = FastAPI(
    title="Clarion Digital Twin API",
    version="1.0.0"
)

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

class SimulationRequest(BaseModel):
    base_data: Dict[str, Any]
    changes: Dict[str, Any]

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

@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# ANALYZE
# =========================
@app.post("/analyze")
def analyze(request: AnalysisRequest, user: str = Depends(get_current_user)):
    try:
        result = run_full_analysis(request.data)
        return {"success": True, "result": result}
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }

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
def submit_answers(
    request: SubmitRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        incoming_answers = request.answers

        if not incoming_answers:
            raise HTTPException(status_code=400, detail="No answers provided")

        rows = []

        for question_id, answer in incoming_answers.items():

            # ✅ FIX: handles "17", 17, and "q17"
            clean_question_id = str(question_id).replace("q", "").replace("Q", "").strip()

            if not clean_question_id.isdigit():
                print("SKIPPING INVALID QUESTION ID:", question_id)
                continue

            rows.append({
                "user_id": user_id,
                "question_id": int(clean_question_id),
                "answer": str(answer),
                "updated_at": datetime.utcnow().isoformat()
            })

        if not rows:
            raise HTTPException(status_code=400, detail="No valid answers provided")

        # 1. Save answers first
        save_res = supabase.table("answers").upsert(
            rows,
            on_conflict="user_id,question_id"
        ).execute()

        print("ANSWERS SAVED:", save_res.data)

        # 2. Fetch all latest answers for this user
        all_answers_res = supabase.table("answers") \
            .select("question_id, answer") \
            .eq("user_id", user_id) \
            .execute()

        all_answers = {
            str(row["question_id"]): row["answer"]
            for row in (all_answers_res.data or [])
        }

        # 3. Try analysis, but do NOT fail answer saving if analysis fails
        analysis = None
        analysis_error = None

        try:
            analysis = run_full_analysis(all_answers)

            supabase.table("analysis").upsert({
                "user_id": user_id,
                "result": analysis,
                "updated_at": datetime.utcnow().isoformat()
            }).execute()

        except Exception as analysis_exc:
            analysis_error = str(analysis_exc)
            print("ANALYSIS ERROR AFTER ANSWER SAVE:", analysis_error)
            print(traceback.format_exc())

        return {
            "success": True,
            "message": "Answers saved successfully",
            "answers": all_answers,
            "analysis": analysis,
            "analysis_error": analysis_error
        }

    except HTTPException:
        raise

    except Exception as e:
        print("SUBMIT ERROR:", e)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
# =========================
# GET SAVED ANSWERS
# =========================
@app.get("/answers")
def get_answers(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("answers") \
            .select("question_id, answer") \
            .eq("user_id", user_id) \
            .execute()

        answers = {
            str(row["question_id"]): row["answer"]
            for row in (res.data or [])
        }

        return {
            "success": True,
            "answers": answers
        }

    except Exception as e:
        print("GET ANSWERS ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# GET SAVED ANALYSIS
# =========================
@app.get("/analysis")
def get_analysis(user_id: str = Depends(get_current_user)):
    try:
        res = supabase.table("analysis") \
            .select("result, updated_at") \
            .eq("user_id", user_id) \
            .order("updated_at", desc=True) \
            .limit(1) \
            .execute()

        if not res.data:
            return {
                "success": True,
                "analysis": None,
                "updated_at": None
            }

        latest = res.data[0]

        return {
            "success": True,
            "analysis": latest.get("result"),
            "updated_at": latest.get("updated_at")
        }

    except Exception as e:
        print("GET ANALYSIS ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))


# =========================
# CHAT
# =========================
@app.post("/chat/message")
def chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        # Create chat if needed
        if not req.chat_id:
            chat = supabase.table("chats").insert({
                "title": "New Chat"
            }).execute()

            chat_id = chat.data[0]["id"]
        else:
            chat_id = req.chat_id

        # Save user message
        save_message(chat_id, "user", req.message)

        # Get history
        history = get_chat_history(chat_id)

        # Get AI response
        answer = ask_ai(req.message, history, user_id)

        # Save AI message
        save_message(chat_id, "assistant", answer)

        return {
            "chat_id": chat_id,
            "answer": answer
        }

    except Exception as e:
        print("CHAT ERROR:", e)
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# FETCH CHATS
# =========================
@app.get("/chats")
def get_chats():
    res = supabase.table("chats").select("*").execute()
    return res.data

@app.get("/chats/{chat_id}")
def get_messages(chat_id: int):
    res = supabase.table("messages") \
        .select("*") \
        .eq("chat_id", chat_id) \
        .order("id") \
        .execute()

    return res.data