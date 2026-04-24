from typing import Dict, Any, List, Optional

# =============================
# RULE 2.1 — TRUST
# =============================
def trust_score(data):
    score = 0

    # engagement measurement
    if data.q4_engagement_measured == "Yes":
        score += 30

    # turnover
    if data.q5_turnover < 25:
        score += 40
    elif data.q5_turnover < 50:
        score += 20

    # role clarity
    if data.q3_roles_clear == "Yes":
        score += 30

    return {
        "score": score,
        "level": "HIGH" if score >= 70 else "LOW"
    }


# =============================
# RULE 2.2 — HEALTHY CONFLICT
# =============================
def conflict_health(data):
    unhealthy = False
    reason = None

    if data.q5_turnover >= 50 and any(x in data.q6_perf_improvements for x in [
        "Stronger leadership/management",
        "Improved communication/collaboration",
        "Better work-life balance"
    ]):
        unhealthy = True
        reason = "Artificial harmony — issues not surfaced"

    if data.q4_engagement_measured == "No" and data.q3_roles_clear == "No":
        unhealthy = True
        reason = "Avoidance pattern — leadership not engaging issues"

    return {
        "status": "UNHEALTHY" if unhealthy else "HEALTHY",
        "reason": reason
    }


# =============================
# RULE 2.3 — COMMITMENT
# =============================
def commitment_score(data):
    if data.q3_roles_clear == "Yes" and data.q9_employee_understanding == "Yes":
        return {
            "score": 90,
            "status": "HIGH"
        }

    if data.q3_roles_clear == "No" and data.q9_employee_understanding == "No":
        return {
            "score": 30,
            "status": "LOW",
            "alert": "Lack of Buy-In — Team doesn't understand roles or direction"
        }

    return {
        "score": 60,
        "status": "MEDIUM"
    }


# =============================
# RULE 2.4 — ACCOUNTABILITY
# =============================
def accountability_score(data):
    base = 50

    # role clarity
    if data.q3_roles_clear == "Yes":
        base += 20

    # turnover impact
    if data.q5_turnover >= 50:
        base -= 20

    # improvement signals
    if any(x in data.q6_perf_improvements for x in [
        "Clearer roles and responsibilities",
        "Better processes/workflows",
        "Stronger leadership/management"
    ]):
        base = 50

    elif any(x in data.q6_perf_improvements for x in [
        "Better tools/technology",
        "Additional headcount"
    ]):
        base = 60

    elif any(x in data.q6_perf_improvements for x in [
        "Recognition/appreciation",
        "More autonomy/empowerment"
    ]):
        base = 40

    return {
        "score": base,
        "alert": "Low Standards Dysfunction" if base < 50 else None
    }


# =============================
# RULE 2.5 — RESULTS ORIENTATION
# =============================
def results_orientation(data):
    concentration = data.q7_knowledge_concentration

    if concentration > 50:
        return {
            "score": 30,
            "alert": "Succession Planning Required"
        }

    elif concentration >= 25:
        return {
            "score": 60
        }

    else:
        return {
            "score": 90
        }


# =============================
# RULE 2.6 — TEAM HEALTH
# =============================
def team_health(data):
    trust = trust_score(data)["score"]
    conflict = 40 if conflict_health(data)["status"] == "UNHEALTHY" else 80
    commitment = commitment_score(data)["score"]
    accountability = accountability_score(data)["score"]
    results = results_orientation(data)["score"]

    avg = (trust + conflict + commitment + accountability + results) / 5

    return {
        "score": avg,
        "alert": "Lencioni Team Health Workshop recommended" if avg < 50 else None
    }


# =============================
# RULE 2.7 — TURNOVER CRISIS
# =============================
def turnover_analysis(data):
    turnover = data.q5_turnover

    if turnover < 25:
        level = "Healthy"
    elif turnover < 50:
        level = "Concerning"
    elif turnover < 75:
        level = "Critical"
    else:
        level = "Crisis"

    alerts = []

    if turnover >= 50:
        alerts.append("HR crisis threatening strategy execution")
        alerts.append("Service quality at risk from turnover")

    return {
        "level": level,
        "alerts": alerts
    }


# =============================
# RULE 2.8 — KNOWLEDGE RISK
# =============================
def knowledge_risk(data):
    concentration = data.q7_knowledge_concentration
    turnover = data.q5_turnover

    if concentration >= 25 and turnover >= 25:
        return {
            "risk": "CRITICAL",
            "actions": [
                "Document critical knowledge",
                "Cross-train personnel",
                "Retention plan for key staff"
            ]
        }

    if concentration > 50:
        return {
            "risk": "CRITICAL",
            "insight": "Single point of failure"
        }

    return {
        "risk": "LOW"
    }


# =============================
# RULE 2.9 — ORG COMPLEXITY
# =============================
def org_complexity(data):
    if data.q2_departments >= 5 and data.q1_employee_count <= 25:
        return {
            "status": "OVER-STRUCTURED",
            "insight": "Too many departments for size"
        }

    if data.q2_departments <= 2 and data.q1_employee_count > 25:
        return {
            "status": "UNDER-STRUCTURED",
            "insight": "Not enough structure for scale"
        }

    return {
        "status": "BALANCED"
    }


# =============================
# RULE 2.10 — ROLE CLARITY IMPACT
# =============================
def role_clarity_impact(data):
    if data.q3_roles_clear == "No":
        return {
            "impact": [
                "Reduces 7S Structure effectiveness",
                "Reduces Staff alignment",
                "Recommend KPI architecture"
            ]
        }

    return {"impact": None}


# =============================
# MAIN
# =============================
def run_silo2(data):
    return {
        "trust": trust_score(data),
        "conflict": conflict_health(data),
        "commitment": commitment_score(data),
        "accountability": accountability_score(data),
        "results": results_orientation(data),
        "team_health": team_health(data),
        "turnover": turnover_analysis(data),
        "knowledge_risk": knowledge_risk(data),
        "complexity": org_complexity(data),
        "role_clarity_impact": role_clarity_impact(data)
    }