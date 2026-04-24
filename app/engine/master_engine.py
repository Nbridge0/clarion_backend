# app/engine/master_engine.py

from typing import Dict, Any

# ✅ IMPORT SILOS (MATCH YOUR FILE NAMES)
from app.silos.silo1_strategy import run_silo1
from app.silos.silo2_hr import run_silo2
from app.silos.silo3_efficiency import run_silo3
from app.silos.silo4_financial import run_silo4
from app.silos.silo5_marketing import run_silo5
from app.silos.silo6_service import run_silo6
from app.silos.silo7_risk import run_silo7

# ✅ CROSS RULES
from app.cross.cross_rules import run_cross_analysis


# =========================
# 🧠 MASTER ENGINE
# =========================
def run_full_analysis(data: Any) -> Dict[str, Any]:
    """
    Runs full Clarion analysis across all silos + cross rules
    """

    # -------------------------
    # RUN ALL SILOS
    # -------------------------
    silo1 = run_silo1(data)
    silo2 = run_silo2(data)
    silo3 = run_silo3(data)
    silo4 = run_silo4(data)
    silo5 = run_silo5(data)
    silo6 = run_silo6(data)
    silo7 = run_silo7(data)

    silos = {
        "strategy": silo1,
        "people": silo2,
        "operations": silo3,
        "financial": silo4,
        "marketing": silo5,
        "service": silo6,
        "risk": silo7,
    }

    # -------------------------
    # CROSS-SILO ANALYSIS
    # -------------------------
    cross = run_cross_analysis(
        data=data,
        silo1=silo1,
        silo2=silo2,
        silo3=silo3,
        silo4=silo4,
        silo5=silo5,
        silo6=silo6,
        silo7=silo7,
    )

    # -------------------------
    # GLOBAL SCORE (OPTIONAL)
    # -------------------------
    scores = []

    for silo in silos.values():
        if isinstance(silo, dict):
            for v in silo.values():
                if isinstance(v, dict) and "score" in v:
                    scores.append(v["score"])
                elif isinstance(v, (int, float)):
                    scores.append(v)

    overall_score = sum(scores) / len(scores) if scores else 0

    # -------------------------
    # FINAL OUTPUT
    # -------------------------
    return {
        "overall_score": round(overall_score, 2),
        "silos": silos,
        "cross_analysis": cross
    }