from typing import Dict, Any, List


# =============================
# RULE 5.1 — SEGMENTATION
# =============================
def segmentation(data):
    segments = data.get("q4_segments") or []
    count = len(segments)

    if count <= 3:
        return {"score": 90, "level": "FOCUSED"}
    elif count <= 6:
        return {"score": 70, "level": "MODERATE"}
    else:
        return {
            "score": 40,
            "level": "FRAGMENTED",
            "risk": "Resources too thinly spread"
        }


# =============================
# RULE 5.2 — TARGETING
# =============================
def targeting(data):
    # Q3a
    if data.get("q3_primary_target") == "Multiple":
        clarity = 40
    else:
        clarity = 90

    # Q3b
    if data.get("q3_objection") == "None":
        objection = 60
    else:
        objection = 80

    # Q3c
    understanding_map = {
        "Very clear": 100,
        "Somewhat clear": 60,
        "Unclear": 30,
        "Not analyzed": 10
    }

    understanding = understanding_map.get(data.get("q3_understanding"), 30)

    score = (clarity * 0.4 + objection * 0.35 + understanding * 0.25)

    return {"score": score}


# =============================
# RULE 5.3 — POSITIONING
# =============================
def positioning(data, silo1=None):
    adv = silo1.get("shared_values", {}).get("score", 50) if silo1 else 50

    advantages = data.get("q5_competitive_advantage") or []
    strength = data.get("q7_strength")

    aligned = strength in advantages
    alignment_score = 90 if aligned else 50

    if data.get("q3_objection") == "None":
        objection_score = 70
    else:
        objection_score = 40

    score = adv * 0.5 + alignment_score * 0.3 + objection_score * 0.2

    return {
        "score": score,
        "alert": "Weak positioning" if score < 60 else None
    }


# =============================
# RULE 5.4 — STP ALIGNMENT
# =============================
def stp_alignment(seg, tar, pos):
    avg = (seg["score"] + tar["score"] + pos["score"]) / 3

    return {
        "score": avg,
        "alert": "STP Misalignment" if avg < 60 else None
    }


# =============================
# RULE 5.5 — ACQUISITION
# =============================
def acquisition(data):
    channels = (data.get("q5_channels") or []) + (data.get("q6_channels") or [])
    channel_count = len(channels)

    if channel_count <= 4:
        penalty = 0
    elif channel_count <= 7:
        penalty = 0.2
    else:
        penalty = 0.5

    inbound_map = {
        "0-20": 10,
        "20-40": 30,
        "40-60": 50,
        "60-80": 70,
        "80-100": 90
    }

    inbound = inbound_map.get(data.get("q1_inbound"), 50)
    social = 100 if data.get("q2_social") == "Yes" else 0

    score = inbound * 0.4 + social * 0.2 + (100 * (1 - penalty)) * 0.4

    return {"score": score}


# =============================
# RULE 5.6 — LEAD BALANCE
# =============================
def lead_balance(data):
    inbound_map = {
        "0-20": 10,
        "20-40": 30,
        "40-60": 50,
        "60-80": 70,
        "80-100": 90
    }

    midpoint = inbound_map.get(data.get("q1_inbound"), 50)

    if midpoint >= 70:
        return "INBOUND_DOMINANT"
    elif midpoint >= 40:
        return "BALANCED"
    else:
        return "OUTBOUND_DEPENDENT"


# =============================
# RULE 5.7 — CHANNEL ALIGNMENT
# =============================
def channel_alignment(data):
    recommendations = []

    segments = data.get("q4_segments") or []
    channels = data.get("q6_channels") or []

    for seg in segments:
        if seg in ["Captains", "HoD"]:
            expected = ["Networking", "Events"]
        else:
            expected = ["Social", "SEO"]

        if not any(ch in channels for ch in expected):
            recommendations.append(f"Missing channels for {seg}")

    return recommendations


# =============================
# RULE 5.8 — OBJECTION SEVERITY
# =============================
def objection_analysis(data):
    high = ["Price", "Value", "Product"]

    objection = data.get("q3_objection")

    if objection in high:
        return {"severity": "HIGH"}
    elif objection == "None":
        return {"severity": "LOW"}
    else:
        return {"severity": "MEDIUM"}


# =============================
# RULE 5.9 — REVENUE SCORE
# =============================
def revenue_score(data, silo4=None, silo6=None):
    recurring = data.get("q3_recurring_revenue", 0)
    concentration = silo4.get("concentration", {}).get("score", 50) if silo4 else 50
    repeat = silo6.get("repeat_score", 50) if silo6 else 50

    score = recurring * 0.5 + concentration * 0.3 + repeat * 0.2

    return score


# =============================
# RULE 5.10 — FUNNEL HEALTH
# =============================
def funnel_health(acq, silo6=None, revenue=50):
    retention = silo6.get("repeat_score", 50) if silo6 else 50

    if acq >= 70 and retention >= 70 and revenue >= 70:
        return "STRONG"

    if acq < 40 or retention < 40:
        return "WEAK"

    return "MODERATE"


# =============================
# MAIN
# =============================
def run_silo5(data, silo1=None, silo4=None, silo6=None):

    seg = segmentation(data)
    tar = targeting(data)
    pos = positioning(data, silo1)

    stp = stp_alignment(seg, tar, pos)

    acq = acquisition(data)
    lead = lead_balance(data)
    channel = channel_alignment(data)
    objection = objection_analysis(data)

    rev = revenue_score(data, silo4, silo6)

    funnel = funnel_health(acq["score"], silo6, rev)

    return {
        "segmentation": seg,
        "targeting": tar,
        "positioning": pos,
        "stp": stp,
        "acquisition": acq,
        "lead_balance": lead,
        "channel_alignment": channel,
        "objection": objection,
        "revenue_score": rev,
        "funnel": funnel
    }