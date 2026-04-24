from typing import Dict, Any, List


# =============================
# RULE 7.1 — LIABILITY RISK
# =============================
def liability_risk(data):
    prevention = []

    if data.q1_contractor_insurance == "Yes":
        prevention.append("STRONG")
    elif data.q1_contractor_insurance == "Sometimes":
        prevention.append("WEAK")
    else:
        prevention.append("ABSENT")

    if data.q8_vendor_backup == "Yes":
        prevention.append("MODERATE")
    else:
        prevention.append("WEAK")

    if data.q4_pi_insurance == "Yes":
        recovery = "STRONG"
    elif data.q4_pi_insurance == "Partial":
        recovery = "MODERATE"
    else:
        recovery = "ABSENT"

    if "ABSENT" in prevention or recovery == "ABSENT":
        return {
            "risk": "HIGH",
            "alert": "Liability protection gap is critical"
        }

    return {"risk": "LOW"}


# =============================
# RULE 7.2 — SANCTIONS / AML
# =============================
def sanctions_risk(data):
    if data.q2_sanctions == "None" or data.q3_ubo == "No":
        return {
            "risk": "CRITICAL",
            "alert": "Critical compliance gap — sanctions screening"
        }

    return {"risk": "MEDIUM"}


# =============================
# RULE 7.3 — FINANCIAL DISTRESS
# =============================
def financial_distress(data, silo4=None):
    runway = data.q5_runway
    concentration = data.q1_customer_concentration
    recurring = data.q3_recurring_revenue

    if runway < 3 and concentration >= 50:
        return {
            "risk": "CRITICAL",
            "alert": "Existential financial risk"
        }

    return {"risk": "MEDIUM"}


# =============================
# RULE 7.4 — RISK IDENTIFICATION
# =============================
def identify_risks(data):
    risks = []

    if data.q12_owner_dependency == "Yes":
        risks.append(("Strategic", "Likely", "Catastrophic"))

    if data.q5_turnover >= 50:
        risks.append(("Operational", "Almost Certain", "Major"))

    if data.q7_knowledge_concentration > 50:
        risks.append(("Operational", "Possible", "Major"))

    if data.q1_customer_concentration >= 50:
        risks.append(("Financial", "Possible", "Catastrophic"))

    if data.q2_suspects_waste == "Yes":
        risks.append(("Financial", "Likely", "Moderate"))

    if data.q1_repeat_customers < 25:
        risks.append(("Financial", "Almost Certain", "Major"))

    return risks


# =============================
# RULE 7.5 — RISK MATRIX
# =============================
def risk_rating(likelihood, impact):
    if impact == "Catastrophic":
        if likelihood in ["Likely", "Almost Certain"]:
            return "CRITICAL"
        elif likelihood == "Possible":
            return "HIGH"
        return "MEDIUM"

    if impact == "Major":
        if likelihood in ["Likely", "Almost Certain"]:
            return "HIGH"
        elif likelihood == "Possible":
            return "MEDIUM"
        return "LOW"

    if impact == "Moderate":
        if likelihood in ["Likely", "Almost Certain"]:
            return "MEDIUM"
        return "LOW"

    return "LOW"


# =============================
# RULE 7.6 — RISK TREATMENT
# =============================
def treatment(level):
    if level == "CRITICAL":
        return "IMMEDIATE MITIGATION"
    if level == "HIGH":
        return "MITIGATE IN 30 DAYS"
    if level == "MEDIUM":
        return "MONITOR"
    return "ACCEPT"


# =============================
# RULE 7.7 — COMPLIANCE MATURITY
# =============================
def compliance(data):
    score = 0

    score += {
        "Automated": 100,
        "Manual": 60,
        "Onboarding": 30,
        "None": 0
    }.get(data.q2_sanctions, 0) * 0.35

    score += {
        "Yes": 100,
        "Sometimes": 40,
        "Bank only": 30,
        "No": 0
    }.get(data.q3_ubo, 0) * 0.35

    score += {
        "Yes": 100,
        "Sometimes": 50,
        "No": 0
    }.get(data.q1_contractor_insurance, 0) * 0.15

    score += {
        "Yes": 100,
        "Informal": 50,
        "No": 0
    }.get(data.q6_referral_policy, 0) * 0.15

    if score >= 75:
        level = "ADVANCED"
    elif score >= 50:
        level = "DEVELOPING"
    elif score >= 25:
        level = "BASIC"
    else:
        level = "NON_EXISTENT"

    return {"score": score, "level": level}


# =============================
# RULE 7.8 — AML RISK
# =============================
def aml(data):
    if data.q3_ubo == "No" or data.q2_sanctions == "None":
        return "CRITICAL"

    if data.q3_ubo == "Sometimes":
        return "HIGH"

    return "MEDIUM"


# =============================
# RULE 7.9 — RESILIENCE
# =============================
def resilience(data):
    runway = data.q5_runway

    if runway >= 12:
        return "STRONG"
    elif runway >= 6:
        return "MODERATE"
    elif runway >= 3:
        return "WEAK"
    else:
        return "CRITICAL"


# =============================
# RULE 7.10 — ENTERPRISE RISK
# =============================
def enterprise_risk(data):
    risks = identify_risks(data)

    critical = 0
    high = 0

    for r in risks:
        level = risk_rating(r[1], r[2])
        if level == "CRITICAL":
            critical += 1
        elif level == "HIGH":
            high += 1

    compliance_score = compliance(data)["score"]
    resilience_score = {
        "STRONG": 100,
        "MODERATE": 70,
        "WEAK": 40,
        "CRITICAL": 0
    }[resilience(data)]

    score = 1.0 - (
        (critical / 5) * 0.25 +
        (high / 10) * 0.15 +
        (compliance_score / 100) * 0.3 +
        (resilience_score / 100) * 0.3
    )

    return {
        "score": score * 100,
        "alert": "Enterprise at risk" if score < 0.5 else None
    }


# =============================
# MAIN
# =============================
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