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


def inbound_score(value):
    text = str(value or "").replace("–", "-")

    if "0-20" in text:
        return 10
    if "20-40" in text:
        return 30
    if "40-60" in text:
        return 50
    if "60-80" in text:
        return 70
    if "80-100" in text:
        return 90

    return 50


def repeat_score(value):
    text = str(value or "").replace("–", "-")

    if "<25" in text:
        return 12.5
    if "25-50" in text:
        return 37.5
    if "50-75" in text:
        return 62.5
    if ">75" in text:
        return 87.5

    return 50


def segmentation(data):
    segments = items(data, 33)
    count = len(segments)

    if not count:
        return {
            "score": None,
            "level": "UNKNOWN"
        }

    if count <= 3:
        return {
            "score": 90,
            "level": "FOCUSED"
        }

    if count <= 6:
        return {
            "score": 70,
            "level": "MODERATE"
        }

    return {
        "score": 40,
        "level": "FRAGMENTED"
    }


def targeting(data):
    targets = items(data, 33)
    objections = items(data, 34)
    understanding_text = str(answer(data, 35)).strip().lower()

    if len(targets) <= 3 and targets:
        target_clarity = 90
    elif targets:
        target_clarity = 60
    else:
        target_clarity = 30

    if "very clear" in understanding_text:
        understanding = 100
    elif "somewhat clear" in understanding_text:
        understanding = 60
    elif "unclear" in understanding_text:
        understanding = 30
    else:
        understanding = 10

    objection_score = (
        80
        if objections
        else 50
    )

    score = (
        target_clarity * 0.45
        + understanding * 0.4
        + objection_score * 0.15
    )

    return {
        "score": round(score, 2)
    }


def positioning(data, silo1=None):
    understanding_text = str(answer(data, 35)).strip().lower()
    advantages = items(data, 2)
    objections = items(data, 34)

    if "very clear" in understanding_text:
        understanding_score = 100
    elif "somewhat clear" in understanding_text:
        understanding_score = 60
    elif "unclear" in understanding_text:
        understanding_score = 30
    else:
        understanding_score = 10

    differentiation_score = 80 if advantages else 30

    objection_penalty = min(len(objections) * 8, 24)

    score = (
        understanding_score * 0.55
        + differentiation_score * 0.45
        - objection_penalty
    )

    score = max(0, min(100, score))

    return {
        "score": round(score, 2),
        "alert": (
            "Competitive positioning needs clarification"
            if score < 60
            else None
        )
    }


def stp_alignment(seg, tar, pos):
    scores = [
        value["score"]
        for value in [seg, tar, pos]
        if value.get("score") is not None
    ]

    if not scores:
        return {
            "score": None,
            "alert": None
        }

    score = sum(scores) / len(scores)

    return {
        "score": round(score, 2),
        "alert": (
            "STP alignment is weak"
            if score < 60
            else None
        )
    }


def acquisition(data):
    inbound = inbound_score(answer(data, 31))
    social = (
        100
        if str(answer(data, 32)).strip() == "Yes"
        else 0
    )

    channels = list(
        dict.fromkeys(
            items(data, 36) + items(data, 37)
        )
    )

    channel_score = min(len(channels) * 15, 100)

    score = (
        inbound * 0.45
        + social * 0.2
        + channel_score * 0.35
    )

    return {
        "score": round(score, 2),
        "channel_count": len(channels)
    }


def lead_balance(data):
    score = inbound_score(answer(data, 31))

    if score >= 70:
        return "INBOUND_DOMINANT"

    if score >= 40:
        return "BALANCED"

    return "OUTBOUND_DEPENDENT"


def channel_alignment(data):
    # No evidence in the assessment establishes which channel
    # each customer segment "should" use.
    return []


def objection_analysis(data):
    objections = items(data, 34)

    if not objections:
        return {
            "severity": "UNKNOWN",
            "reported_objections": []
        }

    severe_terms = (
        "lack of trust",
        "don't see value",
        "product concerns"
    )

    severe = any(
        any(term in value.lower() for term in severe_terms)
        for value in objections
    )

    return {
        "severity": "HIGH" if severe else "MEDIUM",
        "reported_objections": objections
    }


def funnel_health(acq, data):
    retention = repeat_score(answer(data, 38))

    if acq >= 70 and retention >= 70:
        return "STRONG"

    if acq < 40 or retention < 40:
        return "WEAK"

    return "MODERATE"


def run_silo5(data, silo1=None, silo4=None, silo6=None):
    seg = segmentation(data)
    tar = targeting(data)
    pos = positioning(data, silo1)

    acquisition_data = acquisition(data)

    return {
        "segmentation": seg,
        "targeting": tar,
        "positioning": pos,
        "stp": stp_alignment(seg, tar, pos),
        "acquisition": acquisition_data,
        "lead_balance": lead_balance(data),
        "channel_alignment": channel_alignment(data),
        "objection": objection_analysis(data),

        # The assessment doesn't provide sales revenue values.
        "revenue_score": None,

        "funnel": funnel_health(
            acquisition_data["score"],
            data
        )
    }