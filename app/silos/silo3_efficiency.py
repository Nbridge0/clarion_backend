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


def numeric_choice(value, default=0):
    try:
        return int(str(value).strip().split()[0])
    except Exception:
        return default


def digital_intensity(data):
    tools = str(answer(data, 22)).strip()

    tool_score = {
        "Yes": 100,
        "Some": 65,
        "Not enough": 35,
        "None": 0
    }.get(tools, 0)

    automation_score = (
        100 if str(answer(data, 23)).strip() == "Yes" else 0
    )

    ai_score = (
        100 if str(answer(data, 24)).strip() == "Yes" else 0
    )

    ai_areas = items(data, 25)
    ai_breadth = min(len(ai_areas) / 6 * 100, 100)

    readiness = numeric_choice(answer(data, 26)) * 10

    score = (
        tool_score
        + automation_score
        + ai_score
        + ai_breadth
        + readiness
    ) / 5

    return {
        "score": round(score, 2),
        "level": (
            "HIGH"
            if score >= 70
            else "MEDIUM"
            if score >= 45
            else "LOW"
        )
    }


def transformation_management(data):
    sops = str(answer(data, 21)).strip().lower()

    if "all" in sops:
        sop_score = 100
    elif "most" in sops:
        sop_score = 75
    elif "some" in sops:
        sop_score = 40
    elif sops == "no":
        sop_score = 0
    else:
        sop_score = 0

    strategy_score = (
        100 if str(answer(data, 11)).strip() == "Yes" else 0
    )

    understanding = str(answer(data, 10)).strip()

    alignment_score = {
        "Yes": 100,
        "Some": 60,
        "No": 20
    }.get(understanding, 0)

    score = (
        sop_score
        + strategy_score
        + alignment_score
    ) / 3

    return {
        "score": round(score, 2),
        "level": "STRONG" if score >= 60 else "WEAK"
    }


def mit_quadrant(di, tm):
    if di >= 60 and tm >= 60:
        return "DIGIRATI"

    if di >= 60:
        return "FASHIONISTAS"

    if tm >= 60:
        return "CONSERVATIVES"

    return "BEGINNERS"


def bottleneck(data):
    bottlenecks = items(data, 4)
    severity = str(answer(data, 5)).strip()

    return {
        "reported_bottlenecks": bottlenecks,
        "severity": severity
    }


def vendor_risk(data, _bottleneck=None):
    value = str(answer(data, 27)).strip().lower()

    if "highly dependent" in value:
        return {
            "risk": "HIGH",
            "alert": "No pre-vetted Tier-2 alternative for critical dependency"
        }

    if "for some" in value:
        return {"risk": "MEDIUM"}

    if "all critical services" in value:
        return {"risk": "LOW"}

    return {"risk": "UNKNOWN"}


def readiness_gap(data):
    readiness = numeric_choice(answer(data, 26))
    tools = str(answer(data, 22)).strip()
    automation = str(answer(data, 23)).strip()
    sops = str(answer(data, 21)).lower()

    if readiness >= 7 and (
        tools in ["None", "Not enough"]
        or automation == "No"
        or sops == "no"
    ):
        return {
            "warning": "AI readiness perception is ahead of current operational foundations"
        }

    return None


def sop_impact(data):
    sops = str(answer(data, 21)).lower()

    if sops == "no" or "some" in sops:
        return {
            "documentation_gap": True,
            "service_consistency_risk": True
        }

    return None


def ai_priority(data, _bottleneck=None):
    return [
        {"area": value}
        for value in items(data, 25)
    ]


def transformation_roadmap(quadrant):
    if quadrant == "BEGINNERS":
        return [
            "Document priority processes",
            "Address the reported bottlenecks",
            "Pilot automation in one suitable workflow"
        ]

    if quadrant == "FASHIONISTAS":
        return [
            "Review technology usage against business priorities",
            "Standardise core processes",
            "Strengthen change management"
        ]

    if quadrant == "CONSERVATIVES":
        return [
            "Identify suitable automation opportunities",
            "Pilot one AI use case",
            "Measure outcomes before wider deployment"
        ]

    return [
        "Optimise existing systems",
        "Scale proven automation",
        "Evaluate higher-value AI opportunities"
    ]


def run_silo3(data):
    di = digital_intensity(data)
    tm = transformation_management(data)

    quadrant = mit_quadrant(
        di["score"],
        tm["score"]
    )

    return {
        "digital_intensity": di,
        "transformation_management": tm,
        "quadrant": quadrant,
        "bottleneck": bottleneck(data),

        # There is no percentage-waste question.
        "waste_percent": None,
        "waste_signal": (
            "REPORTED"
            if str(answer(data, 29)).strip() == "Yes"
            else "NOT_REPORTED"
        ),

        "vendor_risk": vendor_risk(data),
        "ai_priorities": ai_priority(data),
        "readiness_gap": readiness_gap(data),
        "sop_impact": sop_impact(data),
        "roadmap": transformation_roadmap(quadrant)
    }