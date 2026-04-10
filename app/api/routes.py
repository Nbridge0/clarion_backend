from fastapi import APIRouter
from app.core.engine.reasoning_engine import run_engine

router = APIRouter()

@router.post("/analyze")
def analyze(data: dict):
    result = run_engine(data)
    return serialize(result)


def serialize(obj):
    if isinstance(obj, list):
        return [serialize(x) for x in obj]
    if hasattr(obj, "__dict__"):
        return {k: serialize(v) for k, v in obj.__dict__.items()}
    return obj