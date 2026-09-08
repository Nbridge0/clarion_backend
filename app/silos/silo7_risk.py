from typing import Dict, Any


def answer(data: Dict[str, Any], question_id: int, default=""):
    value = data.get(str(question_id), data.get(question_id, default))
    return value if value is not None else default


def percentage_midpoint(value, default=0):
    text = str(value or "").strip().replace("–", "-")

    mapping = {
        "<5%": 2.5,
        "5-15%": 10,
        "15-25%": 20,
        "25-50%": 37.5,
        "50-75%": 62.5,
        ">75%": 87.5,

        "<10%": 5,
        "10-25%": 17.5,

        "<25%": 12.5,
    }

    if text in mapping:
        return mapping[text]

    if "25-50" in text:
        return 37.5

    if "50-75" in text:
        return 62.5

    if ">75" in text:
        return 87.5

    if ">50" in text:
        return 62.5

    return default


def runway_level(data):
    value = str(answer(data, 48)).strip().replace("–", "-")

    if "<3" in value:
        return {
            "months_band": "<3",
            "score": 15,
            "level": "CRITICAL"
        }

    if "3-6" in value:
        return {
            "months_band": "3-6",
            "score": 40,
            "level": "WEAK"
        }

    if "6-12" in value:
        return {
            "months_band": "6-12",
            "score": 70,
            "level": "MODERATE"
        }

    if ">12" in value:
        return {
            "months_band": ">12",
            "score": 100,
            "level": "STRONG"
        }

    return {
        "months_band": None,
        "score": 50,
        "level": "UNKNOWN"
    }


def liability_risk(data):
    contractor = str(answer(data, 43)).strip()
    pi = str(answer(data, 46)).strip()
    backup = str(answer(data, 27)).strip().lower()

    issues = []

    if contractor == "No":
        issues.append(
            "Sub-contractors are not required to provide proof of insurance"
        )
    elif contractor == "Sometimes":
        issues.append(
            "Sub-contractor insurance evidence is only collected sometimes"
        )

    if pi == "No":
        issues.append(
            "Professional Indemnity insurance does not cover the largest contract"
        )
    elif pi == "Partial":
        issues.append(
            "Professional Indemnity insurance only partially covers the largest contract"
        )

    if "highly dependent" in backup:
        issues.append(
            "No pre-vetted Tier-2 alternative exists for critical suppliers"
        )

    if any(
        "does not" in value.lower()
        or "no pre-vetted" in value.lower()
        for value in issues
    ):
        risk = "HIGH"
    elif issues:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "risk": risk,
        "issues": issues
    }


def sanctions_risk(data):
    sanctions = str(answer(data, 44)).strip().lower()
    ubo = str(answer(data, 45)).strip().lower()

    if (
        "no formal process" in sanctions
        or ubo == "no"
    ):
        return {
            "risk": "HIGH",
            "alert": "Material sanctions or UBO control gap"
        }

    if (
        "on-boarding only" in sanctions
        or "occasionally" in ubo
        or "bank" in ubo
    ):
        return {
            "risk": "MEDIUM"
        }

    if (
        "automated" in sanctions
        and "yes" in ubo
    ):
        return {
            "risk": "LOW"
        }

    return {
        "risk": "MEDIUM"
    }


def financial_distress(data, silo4=None):
    runway = runway_level(data)
    concentration = percentage_midpoint(answer(data, 28))

    if runway["level"] == "CRITICAL":
        return {
            "risk": "HIGH",
            "reason": "Operational runway is below three months"
        }

    if runway["level"] == "WEAK" and concentration >= 50:
        return {
            "risk": "HIGH",
            "reason": "Limited runway is combined with high customer concentration"
        }

    if runway["level"] == "WEAK":
        return {
            "risk": "MEDIUM",
            "reason": "Operational runway is between three and six months"
        }

    return {
        "risk": "LOW"
    }


def compliance(data):
    sanctions = str(answer(data, 44)).strip().lower()
    ubo = str(answer(data, 45)).strip().lower()
    contractor = str(answer(data, 43)).strip().lower()
    pi = str(answer(data, 46)).strip().lower()
    referral = str(answer(data, 47)).strip().lower()

    sanctions_score = 0

    if "automated" in sanctions:
        sanctions_score = 100
    elif "periodic manual" in sanctions:
        sanctions_score = 70
    elif "on-boarding only" in sanctions:
        sanctions_score = 40

    if "yes" in ubo:
        ubo_score = 100
    elif "occasionally" in ubo:
        ubo_score = 55
    elif "bank" in ubo:
        ubo_score = 35
    else:
        ubo_score = 0

    contractor_score = {
        "yes": 100,
        "sometimes": 50,
        "no": 0
    }.get(contractor, 0)

    pi_score = {
        "yes": 100,
        "partial": 50,
        "no": 0
    }.get(pi, 0)

    if "yes" in referral:
        referral_score = 100
    elif "informal" in referral:
        referral_score = 50
    else:
        referral_score = 0

    score = (
        sanctions_score * 0.30
        + ubo_score * 0.25
        + contractor_score * 0.15
        + pi_score * 0.15
        + referral_score * 0.15
    )

    if score >= 80:
        level = "ADVANCED"
    elif score >= 60:
        level = "DEVELOPING"
    elif score >= 35:
        level = "BASIC"
    else:
        level = "WEAK"

    return {
        "score": round(score, 2),
        "level": level
    }


def aml(data):
    sanctions = str(answer(data, 44)).strip().lower()
    ubo = str(answer(data, 45)).strip().lower()

    if "no formal process" in sanctions or ubo == "no":
        return "HIGH"

    if "occasionally" in ubo or "bank" in ubo:
        return "MEDIUM"

    if "automated" in sanctions and "yes" in ubo:
        return "LOW"

    return "MEDIUM"


def resilience(data):
    return runway_level(data)["level"]


def identify_risks(data):
    risks = []

    owner = str(answer(data, 13)).lower()

    if "heavily owner-dependent" in owner:
        risks.append({
            "category": "STRATEGIC",
            "level": "HIGH",
            "evidence": "Business is heavily owner-dependent"
        })

    turnover = percentage_midpoint(answer(data, 18))

    if turnover >= 50:
        risks.append({
            "category": "PEOPLE",
            "level": "HIGH",
            "evidence": f"Employee turnover reported as {answer(data, 18)}"
        })

    concentration = percentage_midpoint(answer(data, 20))

    if concentration > 50:
        risks.append({
            "category": "PEOPLE",
            "level": "HIGH",
            "evidence": "More than half of critical expertise or relationships are concentrated in one person"
        })

    customer_concentration = percentage_midpoint(answer(data, 28))

    if customer_concentration >= 50:
        risks.append({
            "category": "FINANCIAL",
            "level": "HIGH",
            "evidence": f"Customer concentration reported as {answer(data, 28)}"
        })

    if str(answer(data, 29)).strip() == "Yes":
        risks.append({
            "category": "FINANCIAL",
            "level": "MEDIUM",
            "evidence": "The business reports suspected areas of financial waste"
        })

    repeat = percentage_midpoint(answer(data, 38))

    if repeat < 25:
        risks.append({
            "category": "COMMERCIAL",
            "level": "MEDIUM",
            "evidence": f"Repeat-customer rate reported as {answer(data, 38)}"
        })

    return risks


def enterprise_risk(data):
    identified = identify_risks(data)
    compliance_data = compliance(data)
    runway = runway_level(data)

    high_count = sum(
        1
        for risk in identified
        if risk["level"] == "HIGH"
    )

    medium_count = sum(
        1
        for risk in identified
        if risk["level"] == "MEDIUM"
    )

    identified_risk_score = min(
        high_count * 20 + medium_count * 10,
        100
    )

    control_risk = 100 - compliance_data["score"]
    resilience_risk = 100 - runway["score"]

    score = (
        identified_risk_score * 0.35
        + control_risk * 0.35
        + resilience_risk * 0.30
    )

    if score >= 70:
        level = "CRITICAL"
    elif score >= 50:
        level = "HIGH"
    elif score >= 30:
        level = "MEDIUM"
    else:
        level = "LOW"

    return {
        "score": round(score, 2),
        "level": level,
        "alert": (
            "Enterprise risk requires priority attention"
            if level in ["HIGH", "CRITICAL"]
            else None
        )
    }


def run_silo7(data, silo4=None):
    return {
        "liability": liability_risk(data),
        "sanctions": sanctions_risk(data),
        "financial_distress": financial_distress(data, silo4),
        "identified_risks": identify_risks(data),
        "compliance": compliance(data),
        "aml": aml(data),
        "resilience": resilience(data),
        "enterprise_risk": enterprise_risk(data)
    }