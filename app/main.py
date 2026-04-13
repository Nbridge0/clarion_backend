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

# =========================
# 🔐 LOAD ENV
# =========================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing Supabase environment variables")

print("✅ Supabase connected:", SUPABASE_URL)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================
# 🧠 MOCK ANALYSIS ENGINE
# =========================
def run_analysis(data):
    # Replace this with real logic later
    return {
        "score": len(data),
        "insight": "Analysis completed",
        "input_preview": data
    }

# =========================
# 🔐 AUTH SYSTEM
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
# 🚀 APP INIT
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
# 📦 MODELS
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

# =========================
# 🧠 ROOT
# =========================
@app.get("/")
def root():
    return {"status": "running"}

@app.get("/health")
def health():
    return {"status": "ok"}

# =========================
# 🔥 ANALYZE
# =========================
@app.post("/analyze")
def analyze(request: AnalysisRequest, user: str = Depends(get_current_user)):
    try:
        result = run_analysis(request.data)

        return {
            "success": True,
            "result": result
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "trace": traceback.format_exc()
        }

# =========================
# 👤 CREATE USER (PROTECTED)
# =========================
@app.post("/create-user")
def create_user(
    request: CreateUserRequest,
    x_admin_key: str = Header(None)
):
    if x_admin_key != os.getenv("ADMIN_KEY"):
        raise HTTPException(status_code=403, detail="Unauthorized")

    existing = supabase.table("users") \
        .select("*") \
        .eq("email", request.email) \
        .execute()

    if existing.data:
        raise HTTPException(status_code=400, detail="User already exists")

    hashed_pw = bcrypt.hashpw(
        request.password.encode(),
        bcrypt.gensalt()
    ).decode()

    result = supabase.table("users").insert({
        "email": request.email,
        "password": hashed_pw
    }).execute()

    return {
        "success": True,
        "user": {
            "id": result.data[0]["id"],
            "email": result.data[0]["email"]
        }
    }
# =========================
# 🔐 LOGIN
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
# 📝 SUBMIT ANSWERS
# =========================
@app.post("/submit")
def submit_answers(
    request: SubmitRequest,
    user_id: str = Depends(get_current_user)
):
    try:
        rows = []

        for question_id, answer in request.answers.items():
            rows.append({
                "user_id": user_id,
                "question_id": question_id,
                "answer": answer,
                "created_at": datetime.utcnow().isoformat()
            })

        print("📦 INSERTING:", rows)

        res = supabase.table("answers").insert(rows).execute()

        print("✅ RESULT:", res)

        return {
            "success": True,
            "saved": res.data
        }

    except Exception as e:
        print("🔥 ERROR:", str(e))
        raise HTTPException(status_code=500, detail=str(e))
# =========================
# 🔮 SIMULATION
# =========================
@app.post("/simulate")
def simulate(request: SimulationRequest):
    try:
        simulated_data = {
            **request.base_data,
            **request.changes
        }

        return {
            "success": True,
            "base": run_analysis(request.base_data),
            "simulated": run_analysis(simulated_data)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# 🧪 DEBUG
# =========================
@app.post("/debug")
def debug(request: AnalysisRequest):
    return {
        "keys": list(request.data.keys()),
        "preview": request.data
    }

print("🔥 CORRECT MAIN.PY LOADED")