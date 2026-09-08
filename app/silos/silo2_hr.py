from typing import Dict, Any


def answer(data: Dict[str, Any], question_id: int, default=""):
    value = data.get(str(question_id), data.get(question_id, default))
    return value if value is not None else default


def items(data, question_id):
    value = answer(data, question_id, [])

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    if not value:
        return []

    return [x.strip() for x in str(value).split(",") if x.strip()]


def midpoint(value, default=0):
    text = str(value or "").strip().replace("–", "-")

    ranges = {
        "0-5": 2.5,
        "5-10": 7.5,
        "10-25": 17.5,
        "25-50": 37.5,
        ">50": 60,

        "<25%": 12.5,
        "25-50%": 37.5,
        "50-75%": 62.5,
        ">75%": 87.5,

        "<10%": 5,
        "10-25%": 17.5,
        "25-50%": 37.5,
        ">50%": 62.5,
    }

    return ranges.get(text, default)


def trust_score(data):
    score = 0

    if str(answer(data, 17)).strip() == "Yes":
        score += 30

    turnover = midpoint(answer(data, 18))

    if turnover < 25:
        score += 40
    elif turnover < 50:
        score += 20

    roles = str(answer(data, 16)).strip()

    if roles == "Yes":
        score += 30
    elif roles == "Some":
        score += 15

    return {
        "score": score,
        "level": (
            "HIGH"
            if score >= 70
            else "MEDIUM"
            if score >= 50
            else "LOW"
        )
    }


def conflict_health(data):
    # No question directly measures healthy conflict.
    return None


def commitment_score(data):
    roles = str(answer(data, 16)).strip()
    direction = str(answer(data, 10)).strip()

    if roles == "Yes" and direction == "Yes":
        return {"score": 90, "status": "HIGH"}

    if roles == "No" and direction == "No":
        return {
            "score": 30,
            "status": "LOW",
            "alert": "Role clarity and organisational direction are both weak"
        }

    return {"score": 60, "status": "MEDIUM"}


def accountability_score(data):
    roles = str(answer(data, 16)).strip()
    improvements = items(data, 19)

    score = {
        "Yes": 80,
        "Some": 60,
        "No": 35
    }.get(roles, 50)

    if any(
        "clearer role" in x.lower()
        for x in improvements
    ):
        score = min(score, 55)

    return {
        "score": score,
        "alert": (
            "Role clarity is limiting accountability"
            if score < 50
            else None
        )
    }


def results_orientation(data):
    concentration = midpoint(answer(data, 20))

    if concentration > 50:
        return {
            "score": 30,
            "alert": "High key-person concentration"
        }

    if concentration >= 25:
        return {
            "score": 60,
            "alert": "Moderate key-person concentration"
        }

    return {"score": 90}


def team_health(data):
    values = [
        trust_score(data)["score"],
        commitment_score(data)["score"],
        accountability_score(data)["score"],
        results_orientation(data)["score"]
    ]

    score = sum(values) / len(values)

    return {
        "score": round(score, 2),
        "level": (
            "STRONG"
            if score >= 75
            else "MODERATE"
            if score >= 50
            else "WEAK"
        )
    }


def turnover_analysis(data):
    turnover = midpoint(answer(data, 18))

    if turnover < 25:
        level = "HEALTHY"
    elif turnover < 50:
        level = "CONCERNING"
    elif turnover < 75:
        level = "HIGH"
    else:
        level = "CRITICAL"

    return {
        "estimated_range": str(answer(data, 18)),
        "level": level
    }


def knowledge_risk(data):
    concentration = midpoint(answer(data, 20))
    turnover = midpoint(answer(data, 18))

    if concentration > 50:
        risk = "HIGH"
    elif concentration >= 25 and turnover >= 25:
        risk = "HIGH"
    elif concentration >= 25:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "risk": risk,
        "knowledge_concentration": str(answer(data, 20))
    }


def org_complexity(data):
    department_count = len(items(data, 15))
    employee_count = midpoint(answer(data, 14))

    if not department_count or not employee_count:
        return {"status": "UNKNOWN"}

    if department_count >= 5 and employee_count <= 25:
        return {
            "status": "POTENTIALLY_OVER_STRUCTURED",
            "department_count": department_count
        }

    if department_count <= 2 and employee_count > 25:
        return {
            "status": "POTENTIALLY_UNDER_STRUCTURED",
            "department_count": department_count
        }

    return {
        "status": "BALANCED",
        "department_count": department_count
    }


def role_clarity_impact(data):
    roles = str(answer(data, 16)).strip()

    if roles == "No":
        return {
            "impact": "Clear job descriptions and KPIs are not established"
        }

    if roles == "Some":
        return {
            "impact": "Role clarity and KPI coverage are incomplete"
        }

    return {"impact": None}


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