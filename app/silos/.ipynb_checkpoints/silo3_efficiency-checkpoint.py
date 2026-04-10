from app.types.results import Insight


def process_efficiency_silo(data, twin):
    """
    FULL IMPLEMENTATION:
    Rule 3.1 → 3.10
    """

    Q2 = data.get("sop_coverage", "None")  # All / Most / Some / None
    Q3 = data.get("software_usage", "None")  # Yes / Some / Not enough / None
    Q4 = data.get("automation", "No")  # Yes / No
    Q5 = data.get("ai_usage", "No")  # Yes / No
    Q6 = data.get("ai_areas", [])  # list
    Q7 = data.get("digital_readiness", 0)  # 0–10
    Q8 = data.get("bottleneck", "")
    Q8b = data.get("bottleneck_severity", "")
    Q9 = data.get("backup_vendors", "No")  # Yes / Some / No

    silo = {}

    # =========================================================
    # RULE 3.1 — DIGITAL INTENSITY
    # =========================================================
    software_score = {
        "Yes": 100,
        "Some": 60,
        "Not enough": 40,
        "None": 0
    }.get(Q3, 0)

    automation_score = 100 if Q4 == "Yes" else 0
    ai_score = 100 if Q5 == "Yes" else 0
    ai_breadth = (len(Q6) / 6) * 100 if Q6 else 0
    readiness_score = (Q7 / 10) * 100

    digital_intensity = (
        software_score +
        automation_score +
        ai_score +
        ai_breadth +
        readiness_score
    ) / 5

    silo["digital_intensity"] = digital_intensity

    # =========================================================
    # RULE 3.2 — TRANSFORMATION MANAGEMENT
    # =========================================================
    sop_score = {
        "All": 100,
        "Most": 75,
        "Some": 40,
        "None": 0
    }.get(Q2, 0)

    strategy_clarity = twin.silos.get("strategy", {}).get("strategy_clarity", 50)
    employee_alignment = 100 if twin.silos.get("strategy", {}).get("strategy_clarity_label") == "HIGH" else 50

    transformation = (sop_score + strategy_clarity + employee_alignment) / 3

    silo["transformation_management"] = transformation

    # =========================================================
    # RULE 3.3 — MIT QUADRANTS
    # =========================================================
    if digital_intensity >= 60 and transformation >= 60:
        quadrant = "DIGIRATI"

    elif digital_intensity >= 60 and transformation < 60:
        quadrant = "FASHIONISTAS"

        twin.insights.append(Insight(
            "High tech spend but weak governance — risk of waste",
            "Rule 3.3",
            "HIGH"
        ))

    elif digital_intensity < 60 and transformation >= 60:
        quadrant = "CONSERVATIVES"

        twin.insights.append(Insight(
            "Strong processes but underusing technology",
            "Rule 3.3",
            "MEDIUM"
        ))

    else:
        quadrant = "BEGINNERS"

        twin.insights.append(Insight(
            "Early digital stage — high transformation potential",
            "Rule 3.3",
            "HIGH"
        ))

    silo["digital_quadrant"] = quadrant

    # =========================================================
    # RULE 3.4 — BOTTLENECK CLASSIFICATION
    # =========================================================
    bottleneck_map = {
        "Not enough staff/capacity": "PEOPLE",
        "Staff skill gaps/training needs": "PEOPLE",
        "Cash flow/working capital constraints": "FINANCIAL",
        "Inefficient processes/workflows": "PROCESS",
        "Lack of clear procedures/SOPs": "PROCESS",
        "Decision-making delays/approvals": "PROCESS",
        "Technology/system limitations": "TECHNOLOGY",
        "Supplier/vendor dependencies": "VENDOR",
        "Sales/lead generation challenges": "COMMERCIAL",
        "Quality control issues": "QUALITY",
        "No significant bottleneck": None
    }

    bottleneck = bottleneck_map.get(Q8)
    silo["bottleneck"] = bottleneck

    # severity
    silo["bottleneck_severity"] = Q8b

    # =========================================================
    # RULE 3.5 — PROCESS WASTE ESTIMATION
    # =========================================================
    base_waste = {
        "None": 35,
        "Some": 25,
        "Most": 15,
        "All": 5
    }.get(Q2, 35)

    waste = base_waste

    if Q8b == "Critical impact":
        waste += 20

    if twin.silos.get("strategy", {}).get("systems_efficiency", 100) < 50:
        waste += 15

    if Q4 == "No" and len(Q6) > 0:
        waste += 10

    admin = twin.silos.get("strategy", {}).get("staff_alignment", 50)
    if admin < 50:
        waste += 15

    waste = min(waste, 60)

    silo["waste_percentage"] = waste

    # =========================================================
    # RULE 3.6 — VENDOR RISK
    # =========================================================
    if Q9 == "No" and bottleneck == "VENDOR":
        twin.insights.append(Insight(
            "Vendor single point of failure",
            "Rule 3.6",
            "CRITICAL"
        ))

    elif Q9 == "Some":
        twin.insights.append(Insight(
            "Partial vendor risk — audit required",
            "Rule 3.6",
            "MEDIUM"
        ))

    # =========================================================
    # RULE 3.7 — AI PRIORITY MATRIX
    # =========================================================
    ai_priority = {}

    for area in Q6:
        score = 0

        if bottleneck == "COMMERCIAL" and "Sales" in area:
            score += 40

        if bottleneck == "PROCESS" and "Operations" in area:
            score += 40

        if bottleneck == "FINANCIAL" and "Finance" in area:
            score += 40

        if "Better tools/technology" in twin.silos.get("hr", {}).get("improvements", []):
            score += 10

        if Q4 == "No":
            score += 10

        ai_priority[area] = score

    sorted_ai = sorted(ai_priority.items(), key=lambda x: x[1], reverse=True)

    if sorted_ai:
        silo["top_ai_priority"] = sorted_ai[0][0]

        twin.insights.append(Insight(
            f"Start AI pilot in {sorted_ai[0][0]}",
            "Rule 3.7",
            "HIGH"
        ))

    # =========================================================
    # RULE 3.8 — DIGITAL REALITY CHECK
    # =========================================================
    if Q7 >= 7 and (Q3 in ["None", "Not enough"] or Q4 == "No" or Q2 == "None"):
        twin.insights.append(Insight(
            "Digital readiness perception gap",
            "Rule 3.8",
            "HIGH"
        ))

        silo["digital_intensity"] *= 0.6

    # =========================================================
    # RULE 3.9 — SOP IMPACT CROSS-SILO
    # =========================================================
    if Q2 in ["None", "Some"]:
        twin.insights.append(Insight(
            "Weak SOP coverage impacting consistency and accountability",
            "Rule 3.9",
            "HIGH"
        ))

    # =========================================================
    # RULE 3.10 — TRANSFORMATION ROADMAP
    # =========================================================
    roadmap = []

    if quadrant == "BEGINNERS":
        roadmap = [
            "Document core processes",
            "Eliminate primary bottleneck",
            "Pilot automation"
        ]

    elif quadrant == "FASHIONISTAS":
        roadmap = [
            "Audit tech ROI",
            "Standardize processes",
            "Align tech to strategy"
        ]

    elif quadrant == "CONSERVATIVES":
        roadmap = [
            "Identify automation opportunities",
            "Pilot AI",
            "Scale automation"
        ]

    elif quadrant == "DIGIRATI":
        roadmap = [
            "Optimize systems",
            "Advanced AI integration",
            "Build tech moat"
        ]

    silo["transformation_roadmap"] = roadmap

    # =========================================================
    # SAVE SILO
    # =========================================================
    twin.silos["efficiency"] = silo