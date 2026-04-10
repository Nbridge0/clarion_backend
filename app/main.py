from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 🔥 CORS (VERY IMPORTANT for WordPress)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later you can restrict to your domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 📦 Data model
class Data(BaseModel):
    answers: dict

# 🧠 In-memory storage (for now)
stored_data = {}

# 🚀 Root route (test if API works)
@app.get("/")
def root():
    return {"message": "API is running 🚀"}

# 📩 Submit answers from questions page
@app.post("/submit")
def submit(data: Data):
    global stored_data
    stored_data = data.answers
    return {
        "status": "saved",
        "received": stored_data
    }

# 📊 Get results for dashboard
@app.get("/results")
def results():
    return {
        "data": stored_data
    }