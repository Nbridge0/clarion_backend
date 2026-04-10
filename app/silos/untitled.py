from app.types.results import Insight


def process_strategy_silo(data, twin):
    """
    Implements:
    Rule 1.1 → 1.10
    Full McKinsey 7S (partial dependencies)
    Full SWOT builder
    """

    Q5 = data.get("Q5", [])
    Q6 = data.get("Q6", 0)
    Q7 = data.get("Q7", "")
    Q8 = data.get("Q8", "")
    Q9 = data.get("Q9", "")
    Q10 = data.get("Q10", "")
    Q11 = data.get("Q11", [])
    Q12 = data.get("Q12", "")

    silo = {}

    # =========================
    # RULE 1.1 — STRATEGIC CLARITY
    # =========================
    if Q10 == "Yes" and Q9 in ["Yes", "Some"]:
        clarity = 90
        clarity_label = "HIGH"
    elif Q10 == "No" and Q9 == "No":
        clarity = 10
        clarity_label = "CRITICALLY LOW"

        twin.insights.append(Insight(
            "Critical strategic misalignment detected — no plan and employees unclear",
            "Rule 1.1",
            "CRITICAL"
        ))
    else:
        clarity = 50
        clarity_label = "MEDIUM"

    silo["strategy_clarity"] = clarity
    silo["strategy_clarity_label"] = clarity_label

    # =========================
    # RULE 1.2 — SHARED VALUES (7S)
    # =========================

    strong = [
        "Specialized expertise",
        "Unique product/service",
        "Established relationships",
        "Technology",
        "Brand",
        "Quality"
    ]

    commodity = [
        "Lower pricing",
        "Faster delivery",
        "Better customer service",
        "Geographic"
    ]

    if "We don't have a clear competitive advantage" in Q5:
        shared_score = 10

        twin.insights.append(Insight(
            "No competitive differentiation identified",
            "Rule 1.2",
            "HIGH"
        ))

    else:
        strong_count = sum([1 for x in Q5 if any(s in x for s in strong)])
        commodity_count = sum([1 for x in Q5 if any(c in x for c in commodity)])

        if strong_count == 1 and commodity_count == 0:
            shared_score = 90
        elif 2 <= strong_count <= 3 and commodity_count == 0:
            shared_score = 70
        elif strong_count == 0 and commodity_count >= 1:
            shared_score = 50
        elif strong_count >= 1 and commodity_count >= 1:
            shared_score = 65
        else:
            shared_score = 50

    # strength interpretation
    if shared_score >= 70 and Q9 == "Yes":
        shared_strength = "STRONG"
    elif shared_score >= 70:
        shared_strength = "MODERATE"

        twin.insights.append(Insight(
            "Strong advantage exists but employees not aligned",
            "Rule 1.2",
            "MEDIUM"
        ))
    else:
        shared_strength = "WEAK"

        twin.insights.append(Insight(
            "Weak competitive identity — employees lack rally point",
            "Rule 1.2",
            "HIGH"
        ))

    silo["shared_values_score"] = shared_score
    silo["shared_values_strength"] = shared_strength

    # =========================
    # RULE 1.3 — STAFF ALIGNMENT
    # =========================

    admin_time = data.get("admin_percent", 0)

    staff_score = 0

    if Q9 == "Yes":
        staff_score += 40
    elif Q9 == "Some":
        staff_score += 20

    if admin_time < 30:
        staff_score += 30
    elif admin_time < 50:
        staff_score += 15

    if Q12 != "heavily owner-dependent":
        staff_score += 30

    silo["staff_alignment"] = staff_score

    # =========================
    # RULE 1.4 — SYSTEMS (duplication)
    # =========================

    if Q8 == "A lot":
        systems_score = 30
    elif Q8 == "Some":
        systems_score = 60
    else:
        systems_score = 90

    silo["systems_efficiency"] = systems_score

    # =========================
    # RULE 1.5 — SWOT STRENGTHS
    # =========================

    if Q5:
        twin.swot["strengths"].append(Q5[0])

    if Q7:
        twin.swot["strengths"].append(Q7)

    if Q6 >= 4:
        twin.swot["strengths"].append("Strong market position confidence")

    # =========================
    # RULE 1.6 — SWOT WEAKNESSES
    # =========================

    if admin_time > 50:
        twin.swot["weaknesses"].append("High administrative burden")

    if Q8 == "A lot":
        twin.swot["weaknesses"].append("Process duplication")

    if Q10 == "No":
        twin.swot["weaknesses"].append("Lack of strategic documentation")

    if Q12 == "heavily owner-dependent":
        twin.swot["weaknesses"].append("Owner dependency risk")

    challenge_map = {
        "Finding and retaining good people": "Talent acquisition and retention weakness",
        "Managing cash flow": "Cash flow management weakness",
        "Operational inefficiencies/waste": "Operational inefficiency",
        "Lack of time for strategic work": "Leadership capacity constraint",
        "Regulatory/compliance requirements": "Compliance capability gap",
        "Generating consistent revenue/sales": "Revenue consistency weakness"
    }

    challenge = data.get("biggest_challenge")

    if challenge:
        twin.swot["weaknesses"].append(
            challenge_map.get(challenge, challenge)
        )

    # =========================
    # RULE 1.7 — SWOT OPPORTUNITIES
    # =========================

    opportunity_map = {
        "Expanding to new customer segments": "Market expansion opportunity",
        "New product/service offerings": "Product/service diversification",
        "Improving customer retention/upselling": "Revenue expansion from existing customers",
        "Digital marketing/online presence": "Digital channel growth",
        "Strategic partnerships/alliances": "Partnership-driven growth",
        "Technology/automation adoption": "Operational leverage through technology",
        "Developing recurring revenue streams": "Recurring revenue model transformation"
    }

    for o in Q11:
        twin.swot["opportunities"].append(
            opportunity_map.get(o, o)
        )

    if admin_time > 40:
        twin.swot["opportunities"].append(
            "High ROI opportunity from automation"
        )

    # =========================
    # RULE 1.8 — SWOT THREATS
    # =========================

    competitors = data.get("competitors", [])
    twin.swot["threats"].extend(competitors)

    if Q9 == "No":
        twin.swot["threats"].append(
            "Strategic misalignment threatening execution"
        )

    if Q12 == "heavily owner-dependent":
        twin.swot["threats"].append(
            "Succession crisis risk"
        )

    # =========================
    # RULE 1.9 — 7S ALIGNMENT SCORE
    # =========================

    structure = data.get("structure_score", 50)
    skills = data.get("skills_score", 50)
    style = 50

    alignment = (
        clarity +
        structure +
        systems_score +
        shared_score +
        style +
        staff_score +
        skills
    ) / 7

    twin.scores["s7_alignment"] = alignment

    if alignment < 60:
        twin.insights.append(Insight(
            "Critical 7S misalignment detected",
            "Rule 1.9",
            "CRITICAL"
        ))

    # =========================
    # RULE 1.10 — GROWTH REALITY CHECK
    # =========================

    if Q6 >= 4:
        if Q10 == "No" or Q9 == "No" or Q12 == "heavily owner-dependent":
            twin.insights.append(Insight(
                "Growth confidence not supported by foundation",
                "Rule 1.10",
                "CRITICAL"
            ))

    # capital intensive vs runway
    runway = data.get("runway_months", 12)

    capital_growth = [
        "Geographic expansion",
        "Acquiring competitors/businesses",
        "Launch new products/services"
    ]

    if any(x in Q11 for x in capital_growth) and runway < 6:
        twin.insights.append(Insight(
            "Growth strategy requires capital not available",
            "Rule 1.10",
            "CRITICAL"
        ))

    # =========================
    # SAVE SILO
    # =========================

    silo["7s_alignment"] = alignment

    twin.silos["strategy"] = silo