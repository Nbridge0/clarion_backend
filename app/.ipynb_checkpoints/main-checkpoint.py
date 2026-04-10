from fastapi import FastAPI
from app.api.routes import router

app = FastAPI(
    title="Clarion Digital Twin Backend",
    description="Full reasoning engine across 7 silos",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def root():
    return {"message": "Clarion Backend Running"}