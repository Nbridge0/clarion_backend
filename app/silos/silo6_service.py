from app.types.results import Insight


def process_service_silo(data, twin):
    """
    FULL IMPLEMENTATION:
    Rule 6.1 → 6.10
    """

    Q1 = data.get("repeat_customers", 0)  # %
    Q2 = data.get("quality_consistency", 3)  # 1–5
    Q3 = data.get("referral_frequency", 3)  # 1–5
    Q4a = data.get("praise", [])
    Q4b = data.get("complaints", [])

    silo = {}

    # =========================================================
    # RULE 6.1 — RELIABILITY
    # =========================================================
    quality_score = (Q2 / 5) * 50

    if Q1 >= 75:
        repeat_score = 100
    elif Q1 >= 50:
        repeat_score = 75
    elif Q1 >= 25:
        repeat_score = 50
    else:
        repeat_score = 25

    sop = twin.silos.get("efficiency", {}).get("transformation_management", 50)

    reliability = quality_score + (repeat_score * 0.3) + (sop * 0.2)

    silo["reliability"] = reliability

    if reliability < 60:
        twin.insights.append(Insight(
            "Service reliability is weak — standardization required",
            "Rule 6.1",
            "HIGH"
        ))

    # =========================================================
    # RULE 6.2 — ASSURANCE
    # =========================================================
    knowledge = twin.silos.get("hr", {}).get("knowledge_concentration", 50)

    if knowledge < 10:
        expertise = 90
    elif knowledge < 25:
        expertise = 70
    elif knowledge < 50:
        expertise = 50
    else:
        expertise = 30

    role_clarity = twin.silos.get("hr", {}).get("role_clarity", "No")

    role_score = {
        "Yes": 100,
        "Some": 60,
        "No": 20
    }.get(role_clarity, 20)

    if any(x in Q4a for x in ["Expertise", "Professionalism"]):
        praise_score = 90
    elif any(x in Q4a for x in ["Quality"]):
        praise_score = 80
    elif any(x in Q4b for x in ["Quality", "Communication"]):
        praise_score = 30
    elif "We don't track this" in Q4a or "We don't track this" in Q4b:
        praise_score = 50
    else:
        praise_score = 60

    assurance = expertise * 0.4 + role_score * 0.3 + praise_score * 0.3

    silo["assurance"] = assurance

    # =========================================================
    # RULE 6.3 — TANGIBLES
    # =========================================================
    digital = twin.silos.get("efficiency", {}).get("digital_intensity", 50)

    social = twin.silos.get("marketing", {}).get("acquisition_score", 0)
    social_score = 100 if social > 0 else 0

    comp_adv = twin.silos.get("strategy", {}).get("shared_values_score", 50)

    if comp_adv >= 70:
        brand = 80
    elif comp_adv <= 10:
        brand = 40
    else:
        brand = 60

    tangibles = digital * 0.4 + social_score * 0.3 + brand * 0.3

    silo["tangibles"] = tangibles

    # =========================================================
    # RULE 6.4 — EMPATHY
    # =========================================================
    if any(x in Q4a for x in ["Customer service", "Attention", "Going above"]):
        empathy_score = 90
    elif any(x in Q4a for x in ["Flexibility"]):
        empathy_score = 80
    elif any(x in Q4b for x in ["Communication", "Follow-up", "Complexity"]):
        empathy_score = 20
    elif "We don't track this" in Q4a:
        empathy_score = 40
    else:
        empathy_score = 60

    referral_score = (Q3 / 5) * 100

    understanding_map = {
        "Very clear": 100,
        "Somewhat clear": 60,
        "Unclear": 30,
        "We haven't analyzed this": 10
    }

    understanding = understanding_map.get(
        twin.silos.get("marketing", {}).get("customer_understanding", "Unclear"), 30
    )

    empathy = empathy_score * 0.5 + referral_score * 0.3 + understanding * 0.2

    silo["empathy"] = empathy

    # =========================================================
    # RULE 6.5 — RESPONSIVENESS
    # =========================================================
    bottleneck_severity = twin.silos.get("efficiency", {}).get("bottleneck_severity", "")

    severity_map = {
        "No significant bottleneck": 100,
        "Minor annoyance": 70,
        "Moderate impact": 50,
        "Major impact": 30,
        "Critical impact": 10
    }

    bottleneck_score = severity_map.get(bottleneck_severity, 50)

    automation = twin.silos.get("efficiency", {}).get("digital_intensity", 50)
    automation_score = 80 if automation > 50 else 40

    if any("Speed" in x for x in Q4a):
        feedback_score = 90
    elif any("Delays" in x for x in Q4b):
        feedback_score = 20
    elif "We don't track this" in Q4a:
        feedback_score = 50
    else:
        feedback_score = 60

    responsiveness = bottleneck_score * 0.4 + automation_score * 0.3 + feedback_score * 0.3

    silo["responsiveness"] = responsiveness

    # =========================================================
    # RULE 6.6 — OVERALL SERVQUAL
    # =========================================================
    overall = (reliability + assurance + tangibles + empathy + responsiveness) / 5

    silo["service_quality"] = overall

    expectation_gap = (Q3 / 5) - ((5 - Q2) / 5)

    if expectation_gap < -0.3:
        twin.insights.append(Insight(
            "Critical service gap — expectations exceed delivery",
            "Rule 6.6",
            "CRITICAL"
        ))

    if expectation_gap > 0.3:
        twin.insights.append(Insight(
            "Exceeding expectations — pricing opportunity",
            "Rule 6.6",
            "HIGH"
        ))

    # =========================================================
    # RULE 6.7 — CLV
    # =========================================================
    if Q1 >= 75:
        lifespan = 60
        freq = 12
    elif Q1 >= 50:
        lifespan = 36
        freq = 6
    elif Q1 >= 25:
        lifespan = 18
        freq = 4
    else:
        lifespan = 12
        freq = 2

    clv_score = (lifespan * freq) / 100

    if clv_score >= 6:
        clv_segment = "PREMIUM"
    elif clv_score >= 3:
        clv_segment = "HIGH"
    elif clv_score >= 1.5:
        clv_segment = "MEDIUM"
    else:
        clv_segment = "LOW"

    silo["clv"] = clv_score
    silo["clv_segment"] = clv_segment

    # =========================================================
    # RULE 6.8 — CLV STRATEGY
    # =========================================================
    if clv_segment in ["LOW", "MEDIUM"] and Q1 < 50:
        twin.insights.append(Insight(
            "CLV too low — shift to retention strategy",
            "Rule 6.8",
            "HIGH"
        ))

    if clv_segment in ["HIGH", "PREMIUM"]:
        twin.insights.append(Insight(
            "High-value customers — consider VIP programs",
            "Rule 6.8",
            "MEDIUM"
        ))

    # =========================================================
    # RULE 6.9 — RETENTION HEALTH
    # =========================================================
    if Q1 >= 75:
        retention = "EXCELLENT"
    elif Q1 >= 50:
        retention = "GOOD"
    elif Q1 >= 25:
        retention = "FAIR"
    else:
        retention = "POOR"

        twin.insights.append(Insight(
            "Critical retention problem",
            "Rule 6.9",
            "CRITICAL"
        ))

    silo["retention"] = retention

    # =========================================================
    # RULE 6.10 — NPS
    # =========================================================
    promoter = (Q3 / 5) * 100
    detractor = ((5 - Q2) / 5) * 30

    nps = promoter - detractor

    silo["nps"] = nps

    if nps < 0:
        twin.insights.append(Insight(
            "Customer satisfaction crisis",
            "Rule 6.10",
            "CRITICAL"
        ))

    # =========================================================
    # SAVE SILO
    # =========================================================
    twin.silos["service"] = silo