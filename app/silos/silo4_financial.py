from typing import Dict, Any


def answer(data: Dict[str, Any], question_id: int, default=""):
    value = data.get(str(question_id), data.get(question_id, default))
    return value if value is not None else default


def percentage_midpoint(value, default=0):
    text = str(value or "").strip().replace("–", "-")

    ranges = {
        "<5%": 2.5,
        "5-15%": 10,
        "15-25%": 20,
        "25-50%": 37.5,
        "50-75%": 62.5,
        ">75%": 87.5,

        "<25%": 12.5,
        "25-50%": 37.5,
        "50-75%": 62.5,
        ">75%": 87.5,
    }

    return ranges.get(text, default)


def revenue_concentration(data):
    value = str(answer(data, 28)).strip()
    pct = percentage_midpoint(value)

    if pct > 75:
        risk = "CRITICAL"
        score = 20
    elif pct >= 50:
        risk = "HIGH"
        score = 35
    elif pct >= 25:
        risk = "MODERATE"
        score = 55
    elif pct >= 15:
        risk = "LOW"
        score = 80
    else:
        risk = "LOW"
        score = 100

    return {
        "reported_range": value,
        "risk": risk,
        "score": score
    }


def business_model(data):
    value = str(answer(data, 30)).strip()
    recurring = percentage_midpoint(value)

    if recurring >= 75:
        business_type = "HIGH_RECURRING"
        predictability = "HIGH"

    elif recurring >= 50:
        business_type = "MAJORITY_RECURRING"
        predictability = "GOOD"

    elif recurring >= 25:
        business_type = "MIXED"
        predictability = "MEDIUM"

    else:
        business_type = "LOW_RECURRING"
        predictability = "LOW"

    return {
        "reported_recurring_revenue": value,
        "type": business_type,
        "predictability": predictability
    }


def financial_health(data, concentration=None):
    concentration = concentration or revenue_concentration(data)

    recurring = percentage_midpoint(answer(data, 30))
    waste = str(answer(data, 29)).strip()

    stability_score = (
        concentration["score"] * 0.5
        + recurring * 0.5
    )

    risk_points = 0

    if concentration["risk"] in ["HIGH", "CRITICAL"]:
        risk_points += 2
    elif concentration["risk"] == "MODERATE":
        risk_points += 1

    if recurring < 25:
        risk_points += 2
    elif recurring < 50:
        risk_points += 1

    if waste == "Yes":
        risk_points += 1

    if risk_points >= 4:
        risk = "HIGH"
    elif risk_points >= 2:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "revenue_stability_score": round(stability_score, 2),
        "risk_level": risk,
        "suspected_waste": waste
    }


def cash_flow_risk(data, silo7=None):
    # Runway comes directly from Q48.
    runway = str(answer(data, 48)).strip().replace("–", "-")
    waste = str(answer(data, 29)).strip()

    if runway == "<3 months":
        return {
            "risk": "HIGH",
            "reason": "Reported operational runway is below three months"
        }

    if runway == "3-6 months" and waste == "Yes":
        return {
            "risk": "MEDIUM",
            "reason": "Limited runway combined with suspected financial waste"
        }

    return None


def run_silo4(
    data,
    silo1=None,
    silo2=None,
    silo3=None,
    silo6=None,
    silo7=None
):
    concentration = revenue_concentration(data)
    model = business_model(data)
    health = financial_health(data, concentration)

    return {
        "concentration": concentration,
        "business_model": model,

        # These cannot be calculated from the assessment.
        "ccc": None,
        "working_capital": None,
        "net_profit_margin": None,
        "asset_turnover": None,
        "roe": None,

        # Question only asks whether waste is suspected.
        "waste_percent": None,
        "waste_signal": str(answer(data, 29)).strip(),

        "financial_health": health,
        "cash_flow_risk": cash_flow_risk(data, silo7)
    }