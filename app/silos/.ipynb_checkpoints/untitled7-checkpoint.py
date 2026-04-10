from app.types.results import Insight, RiskItem


def process_risk_silo(data, twin):
    """
    FULL IMPLEMENTATION:
    Rule 7.1 → 7.10
    """

    Q1 = data.get("contractor_insurance", "No")  # Yes / Sometimes / No
    Q2 = data.get("sanctions_screening", "None")  # Automated / Periodic / Onboarding / None
    Q3 = data.get("ubo_verification", "No")  # Yes / Occasionally / Bank / No
    Q4 = data.get("pi_insurance", "No")  # Yes / Partial / No
    Q5 = data.get("runway_months", 12)
    Q6 = data.get("referral_policy", "None")  # Written / Informal / None

    silo = {}

    risks = []

    # =========================================================
    # RULE 7.1 — BOWTIE: LIABILITY RISK
    # =========================================================
    prevention = 0

    if Q1 == "Yes":
        prevention += 40
    elif Q1 == "Sometimes":
        prevention += 20

    vendor_backup = twin.silos.get("efficiency", {}).get("bottleneck")

    if vendor_backup == "VENDOR":
        prevention -= 10

    recovery = 0

    if Q4 == "Yes":
        recovery += 40
    elif Q4 == "Partial":
        recovery += 20

    residual = 100 - (prevention + recovery)

    if residual > 60:
        twin.insights.append(Insight(
            "Liability protection gap is critical",
            "Rule 7.1",
            "CRITICAL"
        ))

    # =========================================================
    # RULE 7.2 — SANCTIONS RISK
    # =========================================================
    screening_score = {
        "Automated": 100,
        "Periodic": 60,
        "Onboarding": 30,
        "None": 0
    }.get(Q2, 0)

    ubo_score = {
        "Yes": 100,
        "Occasionally": 40,
        "Bank": 30,
        "No": 0
    }.get(Q3, 0)

    if Q2 == "None" or Q3 == "No":
        twin.insights.append(Insight(
            "Critical sanctions compliance gap",
            "Rule 7.2",
            "CRITICAL"
        ))

        risks.append(RiskItem(
            "Sanctions violation risk",
            "Possible",
            "Catastrophic",
            "CRITICAL",
            "Rule 7.2",
            "Compliance"
        ))

    # =========================================================
    # RULE 7.3 — FINANCIAL DISTRESS
    # =========================================================
    if Q5 > 12:
        runway_score = 100
    elif Q5 >= 6:
        runway_score = 70
    elif Q5 >= 3:
        runway_score = 40
    else:
        runway_score = 0

    concentration = twin.silos.get("financial", {}).get("concentration_score", 50)
    recurring = twin.silos.get("financial", {}).get("business_model", "PROJECT")

    if Q5 < 3 and concentration < 50:
        twin.insights.append(Insight(
            "Existential financial risk",
            "Rule 7.3",
            "CRITICAL"
        ))

    # =========================================================
    # RULE 7.4 — ISO RISK GENERATION
    # =========================================================
    if twin.silos.get("strategy", {}).get("staff_alignment", 100) < 40:
        risks.append(RiskItem(
            "Owner dependency",
            "Likely",
            "Catastrophic",
            "CRITICAL",
            "Rule 7.4",
            "Strategic"
        ))

    if twin.silos.get("hr", {}).get("turnover", 0) >= 50:
        risks.append(RiskItem(
            "High turnover",
            "Almost Certain",
            "Major",
            "HIGH",
            "Rule 7.4",
            "Operational"
        ))

    if twin.silos.get("hr", {}).get("knowledge_concentration", 0) > 50:
        risks.append(RiskItem(
            "Knowledge concentration",
            "Possible",
            "Major",
            "HIGH",
            "Rule 7.4",
            "Operational"
        ))

    # =========================================================
    # RULE 7.5 — RISK MATRIX (AUTO APPLY)
    # =========================================================
    def rate(likelihood, impact):
        if impact == "Catastrophic":
            if likelihood in ["Likely", "Almost Certain"]:
                return "CRITICAL"
            elif likelihood == "Possible":
                return "HIGH"
            else:
                return "MEDIUM"

        if impact == "Major":
            if likelihood in ["Likely", "Almost Certain"]:
                return "HIGH"
            elif likelihood == "Possible":
                return "MEDIUM"
            else:
                return "LOW"

        return "LOW"

    for r in risks:
        r.rating = rate(r.likelihood, r.impact)

    # =========================================================
    # RULE 7.6 — RISK TREATMENT
    # =========================================================
    for r in risks:
        if r.rating == "CRITICAL":
            twin.insights.append(Insight(
                f"Immediate mitigation required: {r.name}",
                "Rule 7.6",
                "CRITICAL"
            ))

    # =========================================================
    # RULE 7.7 — COMPLIANCE MATURITY
    # =========================================================
    referral_score = {
        "Written": 100,
        "Informal": 50,
        "None": 0
    }.get(Q6, 0)

    compliance = (
        screening_score * 0.35 +
        ubo_score * 0.35 +
        (100 if Q1 == "Yes" else 0) * 0.15 +
        referral_score * 0.15
    )

    if compliance >= 75:
        maturity = "ADVANCED"
    elif compliance >= 50:
        maturity = "DEVELOPING"
    elif compliance >= 25:
        maturity = "BASIC"
    else:
        maturity = "NON-EXISTENT"

        twin.insights.append(Insight(
            "Critical compliance deficiency",
            "Rule 7.7",
            "CRITICAL"
        ))

    silo["compliance_maturity"] = maturity

    # =========================================================
    # RULE 7.8 — AML RISK
    # =========================================================
    if Q3 == "Yes" and Q2 in ["Automated", "Periodic"] and Q6 == "Written":
        aml = "MEDIUM"
    elif Q3 == "Occasionally":
        aml = "HIGH"
    else:
        aml = "CRITICAL"

        twin.insights.append(Insight(
            "AML regulatory risk",
            "Rule 7.8",
            "CRITICAL"
        ))

    silo["aml_risk"] = aml

    # =========================================================
    # RULE 7.9 — RESILIENCE
    # =========================================================
    if Q5 > 12:
        resilience = "STRONG"
        resilience_score = 100
    elif Q5 >= 6:
        resilience = "MODERATE"
        resilience_score = 70
    elif Q5 >= 3:
        resilience = "WEAK"
        resilience_score = 40
    else:
        resilience = "CRITICAL"
        resilience_score = 0

        twin.insights.append(Insight(
            "Critical cash runway risk",
            "Rule 7.9",
            "CRITICAL"
        ))

    silo["resilience"] = resilience

    # =========================================================
    # RULE 7.10 — ENTERPRISE RISK SCORE
    # =========================================================
    critical_count = len([r for r in risks if r.rating == "CRITICAL"])
    high_count = len([r for r in risks if r.rating == "HIGH"])

    enterprise_score = 1.0 - (
        (critical_count / 5) * 0.25 +
        (high_count / 10) * 0.15 +
        (compliance / 100) * 0.30 +
        (resilience_score / 100) * 0.30
    )

    enterprise_score *= 100

    silo["enterprise_risk_score"] = enterprise_score

    if enterprise_score < 50:
        twin.insights.append(Insight(
            "Enterprise at risk — board-level intervention required",
            "Rule 7.10",
            "CRITICAL"
        ))

    # =========================================================
    # SAVE
    # =========================================================
    twin.risks.extend(risks)
    twin.silos["risk"] = silo