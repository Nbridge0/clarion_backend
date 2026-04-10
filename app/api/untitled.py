from fastapi import APIRouter
from app.core.engine.reasoning_engine import run_engine

router = APIRouter()


@router.post("/analyze")
def analyze(data: dict):
    result = run_engine(data)
    return result.__dict__