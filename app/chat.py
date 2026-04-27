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

if not OPENAI_API_KEY:
    raise Exception("Missing OPENAI_API_KEY")

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
# AI RESPONSE
# =========================
def ask_ai(message, history, user_id):

    # =========================
    # LOAD USER ANSWERS
    # =========================
    try:
        answers_res = supabase.table("answers") \
            .select("question_id, answer") \
            .eq("user_id", user_id) \
            .execute()

        answers = {
            row["question_id"]: row["answer"]
            for row in (answers_res.data or [])
        }

    except Exception as e:
        print("ANSWERS ERROR:", e)
        answers = {}

    # =========================
    # RUN ANALYSIS
    # =========================
    try:
        from app.engine.master_engine import run_full_analysis
        analysis = run_full_analysis(answers)
    except Exception as e:
        print("ANALYSIS ERROR:", e)
        analysis = {}

    # =========================
    # SYSTEM PROMPT (STRICT CONTROL)
    # =========================
    SYSTEM_PROMPT = f"""
You are PULSE AI, a business intelligence assistant.

Your job is to answer ONLY based on the user's company data.

STRICT RULES:

1. If the user asks something that can be answered using the provided data → answer clearly and concisely.

2. If the question is NOT related to the provided data → respond EXACTLY with:
"Sorry! I can only answer questions related to your data in Pulse. Try asking something within that scope."

3. If the user message is a greeting or casual message (e.g. hi, hello, hey):
→ respond naturally and politely.

4. DO NOT hallucinate
5. DO NOT give generic advice outside the data
6. Be concise and actionable

--- COMPANY DATA ---

ANSWERS:
{answers}

ANALYSIS:
{analysis}
"""

    # =========================
    # BUILD MESSAGES
    # =========================
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    # =========================
    # OPENAI CALL
    # =========================
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "⚠️ AI error. Please try again."