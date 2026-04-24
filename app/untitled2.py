import os
from supabase import create_client
from openai import OpenAI

# -------------------------
# ENV
# -------------------------
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
openai_client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# CHAT HISTORY
# -------------------------
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

# -------------------------
# SAVE MESSAGE
# -------------------------
def save_message(chat_id, role, content):
    try:
        supabase.table("messages").insert({
            "chat_id": chat_id,
            "role": role,
            "content": content
        }).execute()
    except Exception as e:
        print("SAVE ERROR:", e)

# -------------------------
# AI RESPONSE
# -------------------------
def ask_ai(message, history):

    messages = [
        {
            "role": "system",
            "content": "You are a smart business advisor helping companies improve performance."
        }
    ]

    messages.extend(history)

    messages.append({
        "role": "user",
        "content": message
    })

    try:
        res = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7
        )

        return res.choices[0].message.content.strip()

    except Exception as e:
        print("OPENAI ERROR:", e)
        return "⚠️ AI error. Please try again."