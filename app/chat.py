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
            str(row["question_id"]): row["answer"]
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

Your job is to help the user understand and act on their Pulse analysis using ONLY:
1. The user's saved answers
2. The generated Pulse analysis
3. The current conversation history

STRICT RULES:

1. Answer using the user's company data, answers, Pulse analysis, and prior conversation context.

2. If the user asks a short follow-up such as:
   - "tell me more"
   - "explain more"
   - "how?"
   - "why?"
   - "what should I do next?"
   - "give me steps"
   - "continue"
   then treat it as a continuation of the most recent Pulse-related topic in the conversation.

3. If the previous conversation was about a silo, insight, recommendation, risk, answer, or analysis item, continue from that context.

4. If the question is clearly unrelated to the user's Pulse data, business answers, company analysis, silos, recommendations, or previous Pulse-related discussion, respond EXACTLY with:
"Sorry! I can only answer questions related to your data in Pulse. Try asking something within that scope."

5. Do not invent facts about the company.
6. Do not give generic business advice unless it is clearly connected to the user's answers or Pulse analysis.
7. Be practical, concise, and actionable.
8. When giving steps, base them on the selected recommendation, the relevant silo, and the user's saved answers/analysis.

--- USER ANSWERS ---
{answers}

--- PULSE ANALYSIS ---
{analysis}
"""

    # =========================
    # BUILD MESSAGES
    # =========================
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    clean_history = []

    for item in history:
        role = item.get("role")
        content = item.get("content")

        if role in ["user", "assistant"] and content:
            clean_history.append({
                "role": role,
                "content": content
            })

    messages.extend(clean_history)

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