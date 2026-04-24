from typing import Dict, Any, List


# =============================
# RULE 6.1 — RELIABILITY
# =============================
def reliability(data, silo3=None):
    quality_score = (data.q2_quality or 0) / 5 * 50

    repeat_map = {
        "over_75": 100,
        "50_75": 75,
        "25_50": 50,
        "under_25": 25
    }

    repeat_pct = data.q1_repeat_customers

    if repeat_pct >= 75:
        repeat_score = 100
    elif repeat_pct >= 50:
        repeat_score = 75
    elif repeat_pct >= 25:
        repeat_score = 50
    else:
        repeat_score = 25

    sop_map = {
        "All": 100,
        "Most": 75,
        "Some": 40,
        "None": 0
    }

    sop_score = sop_map.get(data.q2_sops, 40)

    total = quality_score + repeat_score * 0.3 + sop_score * 0.2

    return {
        "score": total,
        "alert": "Standardize service delivery" if total < 60 else None
    }


# =============================
# RULE 6.2 — ASSURANCE
# =============================
def assurance(data, silo2=None):
    concentration = data.q7_knowledge_concentration

    if concentration < 10:
        expertise = 90
    elif concentration < 25:
        expertise = 70
    elif concentration < 50:
        expertise = 50
    else:
        expertise = 30

    role_map = {
        "Yes": 100,
        "Some": 60,
        "No": 20
    }

    role_score = role_map.get(data.q3_roles_clear, 20)

    if "Expertise" in (data.q4a_praise or []):
        praise = 90
    elif "Quality" in (data.q4a_praise or []):
        praise = 80
    elif "None" in (data.q4a_praise or []):
        praise = 50
    else:
        praise = 60

    total = expertise * 0.4 + role_score * 0.3 + praise * 0.3

    return {"score": total}


# =============================
# RULE 6.3 — TANGIBLES
# =============================
def tangibles(data, silo3=None, silo5=None):
    digital = silo3.get("digital_intensity", {}).get("score", 50) if silo3 else 50

    social = 100 if data.q2_social == "Yes" else 0

    if "We don't have a clear competitive advantage" in (data.q5_competitive_advantage or []):
        brand = 40
    elif data.q5_competitive_advantage:
        brand = 80
    else:
        brand = 60

    total = digital * 0.4 + social * 0.3 + brand * 0.3

    return {"score": total}


# =============================
# RULE 6.4 — EMPATHY
# =============================
def empathy(data):
    if any(x in (data.q4a_praise or []) for x in [
        "Customer service",
        "Going above and beyond",
        "Attention to detail"
    ]):
        praise = 90
    elif "Flexibility" in (data.q4a_praise or []):
        praise = 80
    elif "None" in (data.q4a_praise or []):
        praise = 40
    else:
        praise = 60

    referral = (data.q3_referral or 0) / 5 * 30

    understanding_map = {
        "Very clear": 100,
        "Somewhat clear": 60,
        "Unclear": 30,
        "Not analyzed": 10
    }

    understanding = understanding_map.get(data.q3_understanding, 30)

    total = praise * 0.5 + referral + understanding * 0.2

    return {"score": total}


# =============================
# RULE 6.5 — RESPONSIVENESS
# =============================
def responsiveness(data, silo3=None):
    bottleneck_map = {
        "None": 100,
        "Minor": 70,
        "Moderate": 50,
        "Major": 30,
        "Critical": 10
    }

    bottleneck = bottleneck_map.get(data.q8b_severity, 50)

    automation = 80 if data.q4_automation == "Yes" else 40

    if "Speed" in (data.q4a_praise or []):
        feedback = 90
    elif "Delays" in (data.q4b_complaints or []):
        feedback = 20
    elif "None" in (data.q4a_praise or []):
        feedback = 50
    else:
        feedback = 60

    total = bottleneck * 0.4 + automation * 0.3 + feedback * 0.3

    return {"score": total}


# =============================
# RULE 6.6 — SERVQUAL
# =============================
def servqual(data, silo2=None, silo3=None):
    r = reliability(data, silo3)["score"]
    a = assurance(data, silo2)["score"]
    t = tangibles(data, silo3)["score"]
    e = empathy(data)["score"]
    rs = responsiveness(data, silo3)["score"]

    avg = (r + a + t + e + rs) / 5

    gap = (data.q3_referral or 0) / 5 - ((5 - (data.q2_quality or 0)) / 5)

    return {
        "score": avg,
        "gap": gap,
        "alert": "Critical service gap" if gap < -0.3 else None
    }


# =============================
# RULE 6.7 — CLV
# =============================
def clv(data, silo4=None):
    repeat = data.q1_repeat_customers

    if repeat >= 75:
        lifespan = 60
    elif repeat >= 50:
        lifespan = 36
    elif repeat >= 25:
        lifespan = 18
    else:
        lifespan = 12

    recurring = data.q3_recurring_revenue

    if recurring >= 75:
        freq = 12
    elif recurring >= 50:
        freq = 6
    elif recurring >= 25:
        freq = 4
    else:
        freq = 2

    score = (lifespan * freq) / 100

    if score >= 6:
        segment = "PREMIUM"
    elif score >= 3:
        segment = "HIGH"
    elif score >= 1.5:
        segment = "MEDIUM"
    else:
        segment = "LOW"

    return {
        "score": score,
        "segment": segment
    }


# =============================
# RULE 6.8 — CLV IMPACT
# =============================
def clv_impact(clv_data, data):
    if clv_data["segment"] in ["LOW", "MEDIUM"] and data.q1_repeat_customers < 50:
        return "Shift focus to retention"

    if clv_data["segment"] in ["HIGH", "PREMIUM"]:
        return "Invest in high-value customers"

    return None


# =============================
# RULE 6.9 — RETENTION
# =============================
def retention(data):
    repeat = data.q1_repeat_customers

    if repeat >= 75:
        return "EXCELLENT"
    elif repeat >= 50:
        return "GOOD"
    elif repeat >= 25:
        return "FAIR"
    else:
        return "POOR"


# =============================
# RULE 6.10 — NPS
# =============================
def nps(data):
    promoter = (data.q3_referral or 0) / 5 * 100
    detractor = ((5 - (data.q2_quality or 0)) / 5) * 30

    score = promoter - detractor

    if score >= 50:
        level = "EXCELLENT"
    elif score >= 20:
        level = "GOOD"
    elif score >= 0:
        level = "NEEDS_IMPROVEMENT"
    else:
        level = "CRITICAL"

    return {
        "score": score,
        "level": level
    }


# =============================
# MAIN
# =============================
def run_silo6(data, silo2=None, silo3=None, silo4=None):

    serv = servqual(data, silo2, silo3)
    clv_data = clv(data, silo4)

    return {
        "reliability": reliability(data, silo3),
        "assurance": assurance(data, silo2),
        "tangibles": tangibles(data, silo3),
        "empathy": empathy(data),
        "responsiveness": responsiveness(data, silo3),
        "servqual": serv,
        "clv": clv_data,
        "clv_impact": clv_impact(clv_data, data),
        "retention": retention(data),
        "nps": nps(data),
        "repeat_score": data.q1_repeat_customers
    }