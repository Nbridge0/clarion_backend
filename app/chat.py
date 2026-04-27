import os
from dotenv import load_dotenv
from supabase import create_client
from openai import OpenAI

# =========================
# LOAD ENV
# =========================
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise Exception("Missing Supabase ENV in chat.py")

# =========================
# CLIENTS
# =========================
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# =========================
# CHAT HISTORY
# =========================
def get_chat_history(chat_id):
    try:
        res = supabase.table("messages") \
            .select("role, content") \
            .eq("chat_id", chat_id) \
            .order("id") \
            .execute()

        return res.data or []
    except Exception as e:
        print("HISTORY ERROR:", e)
        return []

# =========================
# SAVE MESSAGE
# =========================
def save_message(chat_id, role, content):
    try:
        supabase.table("messages").insert({
            "chat_id": chat_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        print("SAVE ERROR:", e)

# =========================
# AI RESPONSE (UPDATED 🔥)
# =========================
def ask_ai(message, history, user_id=None):

    # =========================
    # 1️⃣ LOAD USER ANSWERS
    # =========================
    answers_res = supabase.table("answers") \
        .select("question_id, answer") \
        .eq("user_id", user_id) \
        .execute()

    answers = {
        row["question_id"]: row["answer"]
        for row in (answers_res.data or [])
    }

    # =========================
    # 2️⃣ RUN ANALYSIS ENGINE
    # =========================
    try:
        from app.engine.master_engine import run_full_analysis
        analysis = run_full_analysis(answers)
    except Exception as e:
        print("ANALYSIS ERROR:", e)
        analysis = {}

    # =========================
    # 3️⃣ SYSTEM PROMPT
    # =========================
    SYSTEM_PROMPT = f"""
You are PULSE AI, a strict business intelligence assistant.

RULES:
- ONLY use the provided company data
- DO NOT give generic advice
- DO NOT hallucinate
- If missing data → say:
"I don’t have enough data from your assessment to answer that."

Be concise and actionable.

COMPANY DATA:

ANSWERS:
{answers}

ANALYSIS:
{analysis}
"""

    # =========================
    # 4️⃣ BUILD MESSAGES
    # =========================
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": message
    })

    # =========================
    # 5️⃣ OPENAI CALL
    # =========================
    try:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )

        return res.choices[0].message.content.strip()

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "⚠️ AI error. Please try again."