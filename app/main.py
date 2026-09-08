import os
import uuid
import traceback
import bcrypt

from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from io import BytesIO
from fastapi.responses import StreamingResponse

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph
)

from dotenv import load_dotenv
from supabase import create_client

from app.engine.master_engine import (
    run_full_analysis,
    run_incremental_analysis
)
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

class ProgressRequest(BaseModel):
    current_question: int
    completed: bool = False

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
            raise HTTPException(
                status_code=400,
                detail="No valid answers provided"
            )


        incoming_question_ids = [
            int(
                row["question_id"]
            )
            for row in rows
        ]


        existing_answers_res = (
            supabase
            .table("answers")
            .select(
                "question_id, answer, updated_at"
            )
            .eq(
                "user_id",
                user_id
            )
            .in_(
                "question_id",
                incoming_question_ids
            )
            .order(
                "updated_at",
                desc=True,
                nullsfirst=False
            )
            .execute()
        )


        existing_answers = {}

        for existing_row in (
            existing_answers_res.data
            or []
        ):

            raw_existing_question_id = str(
                existing_row.get(
                    "question_id"
                )
                or ""
            ).strip()

            clean_existing_question_id = (
                raw_existing_question_id
                .replace(
                    "q",
                    ""
                )
                .replace(
                    "Q",
                    ""
                )
                .strip()
            )

            if not clean_existing_question_id.isdigit():
                continue

            if clean_existing_question_id in existing_answers:
                continue

            existing_answers[
                clean_existing_question_id
            ] = str(
                existing_row.get(
                    "answer"
                )
                or ""
            )


        changed_question_ids = []

        for row in rows:

            question_id = int(
                row["question_id"]
            )

            question_key = str(
                question_id
            )

            new_answer = str(
                row.get(
                    "answer"
                )
                or ""
            )

            old_answer = existing_answers.get(
                question_key
            )

    # New question or genuinely changed answer.
            if (
                old_answer is None
                or old_answer != new_answer
            ):
                changed_question_ids.append(
                    question_id
                )


        print(
            "ACTUALLY CHANGED QUESTIONS:",
            {
                "submitted": incoming_question_ids,
                "changed": changed_question_ids
            }
        )


# =========================================================
# SAVE THE NEW AUTHORITATIVE ANSWERS
# =========================================================

        save_res = (
            supabase
            .table("answers")
            .upsert(
                rows,
                on_conflict="user_id,question_id"
            )
            .execute()
        )

        print(
            "ANSWERS SAVED:",
            save_res.data
        )

        
        # =========================================================
        # 2. FETCH THE LATEST AUTHORITATIVE ANSWER PER QUESTION
        # =========================================================
        all_answers_res = (
            supabase
            .table("answers")
            .select("question_id, answer, updated_at")
            .eq("user_id", user_id)
            .order(
                "updated_at",
                desc=True,
                nullsfirst=False
            )
            .execute()
        )

        all_answers = {}

        for row in (all_answers_res.data or []):

            raw_question_id = str(
                row.get("question_id") or ""
            ).strip()

            clean_question_id = (
                raw_question_id
                .replace("q", "")
                .replace("Q", "")
                .strip()
            )

            if not clean_question_id.isdigit():
                continue

            numeric_question_id = int(
                clean_question_id
            )

            if (
                numeric_question_id < 1
                or numeric_question_id > 48
            ):
                continue

            clean_question_id = str(
                numeric_question_id
            )

            if clean_question_id in all_answers:
                continue

            all_answers[
                clean_question_id
            ] = row.get(
                "answer"
            )


        print(
            "LATEST AUTHORITATIVE ANSWERS:",
            all_answers
        )

        print(
            "PULSE ANSWERS BEFORE ANALYSIS:",
            {
                "q8": all_answers.get("8"),
                "q10": all_answers.get("10"),
                "q11": all_answers.get("11"),
                "q18": all_answers.get("18"),
                "q20": all_answers.get("20"),
                "q38": all_answers.get("38"),
                "q48": all_answers.get("48"),
            }
        )


        # =========================================================
        # LOAD CURRENT SAVED ANALYSIS
        # =========================================================

        previous_analysis = None

        try:
            previous_analysis_res = (
                supabase
                .table("analysis")
                .select("result")
                .eq("user_id", user_id)
                .order(
                    "updated_at",
                    desc=True
                )
                .limit(1)
                .execute()
            )

            if previous_analysis_res.data:
                previous_analysis = (
                    previous_analysis_res
                    .data[0]
                    .get("result")
                )

        except Exception as previous_analysis_error:
            print(
                "PREVIOUS ANALYSIS LOAD WARNING:",
                {
                    "error_type": type(
                        previous_analysis_error
                    ).__name__,
                    "error": str(
                        previous_analysis_error
                    )
                }
            )
        # 3. Try analysis, but do NOT fail answer saving if analysis fails
        analysis = None
        analysis_error = None
        updated_at = datetime.utcnow().isoformat()

        try:
            analysis = run_incremental_analysis(
                data=all_answers,
                changed_question_ids=changed_question_ids,
                previous_analysis=previous_analysis
            )

            analysis_save_res = supabase.table("analysis").upsert(
                {
                    "user_id": user_id,
                    "result": analysis,
                    "updated_at": updated_at
                },
                on_conflict="user_id"
            ).execute()

            print("ANALYSIS SAVED:", analysis_save_res.data)

        except Exception as analysis_exc:
            analysis_error = str(analysis_exc)
            print("ANALYSIS ERROR AFTER ANSWER SAVE:", analysis_error)
            print(traceback.format_exc())

        return {
            "success": True,
            "message": "Answers saved successfully",
            "answers": all_answers,
            "analysis": analysis,
            "analysis_error": analysis_error,
            "updated_at": updated_at
        }

    except HTTPException:
        raise

    except Exception as e:
        print("SUBMIT ERROR:", e)
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

# =========================
# SAVE ASSESSMENT PROGRESS
# =========================
@app.post("/progress")
def save_progress(
    request: ProgressRequest,
    user_id: str = Depends(get_current_user)
):
    try:

        current_question = int(request.current_question)

        if current_question < 1:
            current_question = 1

        if current_question > 48:
            current_question = 48

        supabase.table("assessment_progress").upsert(
            {
                "user_id": user_id,
                "current_question": current_question,
                "completed": bool(request.completed),
                "updated_at": datetime.utcnow().isoformat()
            },
            on_conflict="user_id"
        ).execute()

        return {
            "success": True,
            "current_question": current_question,
            "completed": bool(request.completed)
        }

    except Exception as e:
        print("SAVE PROGRESS ERROR:", e)
        print(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# =========================
# GET SAVED ANSWERS + RESUME POSITION
# =========================
@app.get("/answers")
def get_answers(user_id: str = Depends(get_current_user)):
    try:
        res = (
            supabase
            .table("answers")
            .select("question_id, answer, updated_at")
            .eq("user_id", user_id)
            .order(
                "updated_at",
                desc=True,
                nullsfirst=False
            )
            .execute()
        )

        rows = res.data or []

        answers = {}

        for row in rows:

            raw_question_id = str(
                row.get("question_id") or ""
            ).strip()

            clean_question_id = (
                raw_question_id
                .replace("q", "")
                .replace("Q", "")
                .strip()
            )

            if not clean_question_id.isdigit():
                continue

            numeric_question_id = int(
                clean_question_id
            )

            if (
                numeric_question_id < 1
                or numeric_question_id > 48
            ):
                continue

            clean_question_id = str(
                numeric_question_id
            )

            if clean_question_id in answers:
                continue

            answers[
                clean_question_id
            ] = row.get(
                "answer"
            )

        progress_res = (
            supabase
            .table("assessment_progress")
            .select("current_question, completed")
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        if progress_res.data:

            progress = progress_res.data[0]

            current_question = int(
                progress.get("current_question") or 1
            )

            completed = bool(
                progress.get("completed", False)
            )

        else:

            answered_question_ids = set()

            for row in rows:
                raw_question_id = str(
                    row.get("question_id") or ""
                ).strip()

                clean_question_id = (
                    raw_question_id
                    .replace("q", "")
                    .replace("Q", "")
                    .strip()
                )

                if clean_question_id.isdigit():

                    question_id = int(
                        clean_question_id
                    )

                    if 1 <= question_id <= 48:
                        answered_question_ids.add(
                            question_id
                        )

            completed = len(answered_question_ids) >= 48

            if completed:
                current_question = 48
            else:
                current_question = next(
                    (
                        question_id
                        for question_id in range(1, 49)
                        if question_id not in answered_question_ids
                    ),
                    48
                )

        return {
            "success": True,
            "answers": answers,
            "current_question": current_question,
            "completed": completed
        }

    except Exception as e:
        print("GET ANSWERS ERROR:", e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

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
# DOWNLOAD ANALYSIS PDF
# =========================

def escape_pdf_text(value):
    text = str(value or "")

    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )


@app.get("/analysis/pdf")
def download_analysis_pdf(
    user_id: str = Depends(get_current_user)
):
    try:
        res = (
            supabase
            .table("analysis")
            .select("result, updated_at")
            .eq("user_id", user_id)
            .order("updated_at", desc=True)
            .limit(1)
            .execute()
        )

        if not res.data:
            raise HTTPException(
                status_code=404,
                detail="No analysis is available for this account yet."
            )

        latest = res.data[0]

        analysis = latest.get("result")
        updated_at = latest.get("updated_at")

        if not analysis:
            raise HTTPException(
                status_code=404,
                detail="No analysis is available for this account yet."
            )

        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=45,
            leftMargin=45,
            topMargin=45,
            bottomMargin=45,
            title="Pulse Ontology Analysis"
        )

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            "PulseTitle",
            parent=styles["Title"],
            fontSize=22,
            leading=27,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#252668"),
            spaceAfter=10
        )

        subtitle_style = ParagraphStyle(
            "PulseSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#7A83A5"),
            spaceAfter=18
        )

        heading_style = ParagraphStyle(
            "PulseHeading",
            parent=styles["Heading2"],
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#252668"),
            spaceBefore=14,
            spaceAfter=7
        )

        body_style = ParagraphStyle(
            "PulseBody",
            parent=styles["BodyText"],
            fontSize=10,
            leading=15,
            textColor=colors.HexColor("#26354D"),
            spaceAfter=7
        )

        story = []

        story.append(
            Paragraph(
                "PULSE - ONTOLOGY OVERVIEW",
                title_style
            )
        )

        story.append(
            Paragraph(
                "INTELLIGENCE MAPPING",
                subtitle_style
            )
        )

        if updated_at:
            story.append(
                Paragraph(
                    "Analysis updated: " +
                    escape_pdf_text(updated_at),
                    subtitle_style
                )
            )

        def add_value(label, value):
            if value is None:
                return

            clean_label = (
                str(label)
                .replace("_", " ")
                .strip()
                .title()
            )

            if isinstance(value, dict):
                if clean_label:
                    story.append(
                        Paragraph(
                            escape_pdf_text(clean_label),
                            heading_style
                        )
                    )

                for child_key, child_value in value.items():
                    add_value(
                        child_key,
                        child_value
                    )

                return

            if isinstance(value, list):
                if clean_label:
                    story.append(
                        Paragraph(
                            escape_pdf_text(clean_label),
                            heading_style
                        )
                    )

                for item in value:
                    if isinstance(item, (dict, list)):
                        add_value("", item)
                    else:
                        story.append(
                            Paragraph(
                                "- " + escape_pdf_text(item),
                                body_style
                            )
                        )

                return

            if clean_label:
                story.append(
                    Paragraph(
                        escape_pdf_text(clean_label),
                        heading_style
                    )
                )

            story.append(
                Paragraph(
                    escape_pdf_text(value),
                    body_style
                )
            )

        if isinstance(analysis, dict):
            for key, value in analysis.items():
                add_value(key, value)
        else:
            story.append(
                Paragraph(
                    escape_pdf_text(analysis),
                    body_style
                )
            )

        doc.build(story)

        buffer.seek(0)

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition":
                    'attachment; filename="pulse-ontology-analysis.pdf"'
            }
        )

    except HTTPException:
        raise

    except Exception as e:
        print(
            "DOWNLOAD ANALYSIS PDF ERROR:",
            e
        )
        print(traceback.format_exc())

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )



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