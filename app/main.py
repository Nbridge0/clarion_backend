from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any
from pydantic import BaseModel
import traceback

# ✅ CORRECT IMPORT BASED ON YOUR STRUCTURE
try:
    from app.core.engine import run_analysis
except:
    # fallback if function is inside a file
    try:
        from app.core.engine.main import run_analysis
    except:
        try:
            from app.core.engine.processor import run_analysis
        except:
            def run_analysis(data):
                return {
                    "error": "run_analysis not found in app/core/engine",
                    "received": data
                }


app = FastAPI(
    title="Clarion Digital Twin API",
    version="1.0.0"
)

# ✅ WordPress connection
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
# 🔥 MAIN ENDPOINT
# =========================
@app.post("/analyze")
def analyze(request: AnalysisRequest):
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