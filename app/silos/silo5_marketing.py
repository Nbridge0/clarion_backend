from app.types.results import Insight


def process_marketing_silo(data, twin):
    """
    FULL IMPLEMENTATION:
    Rule 5.1 → 5.10
    """

    Q1 = data.get("inbound_range", "0-20")  # string range
    Q2 = data.get("social_media", "No")  # Yes / No
    Q3a = data.get("targeting_mode", "Multiple")  # Single / Multiple
    Q3b = data.get("objection", "")
    Q3c = data.get("customer_understanding", "Unclear")
    Q4 = data.get("audiences", [])
    Q5 = data.get("channels_primary", [])
    Q6 = data.get("channels_secondary", [])

    silo = {}

    # =========================================================
    # RULE 5.1 — SEGMENTATION
    # =========================================================
    count = len(Q4)

    if count <= 3:
        segmentation_score = 90
        segmentation_label = "FOCUSED"

    elif count <= 6:
        segmentation_score = 70
        segmentation_label = "MODERATE"

    else:
        segmentation_score = 40
        segmentation_label = "FRAGMENTED"

        twin.insights.append(Insight(
            "Too many target segments — marketing diluted",
            "Rule 5.1",
            "HIGH"
        ))

    silo["segmentation_score"] = segmentation_score

    # =========================================================
    # RULE 5.2 — TARGETING
    # =========================================================
    if Q3a == "Single":
        target_clarity = 90
    else:
        target_clarity = 40

    if Q3b and Q3b != "We don't encounter much resistance":
        objection_score = 80
    else:
        objection_score = 60

    understanding_map = {
        "Very clear": 100,
        "Somewhat clear": 60,
        "Unclear": 30,
        "We haven't analyzed this": 10
    }

    understanding_score = understanding_map.get(Q3c, 30)

    targeting_score = (
        target_clarity * 0.4 +
        objection_score * 0.35 +
        understanding_score * 0.25
    )

    silo["targeting_score"] = targeting_score

    # =========================================================
    # RULE 5.3 — POSITIONING
    # =========================================================
    comp_adv = twin.silos.get("strategy", {}).get("shared_values_score", 50)

    if comp_adv >= 70:
        advantage_score = 90
    elif comp_adv >= 50:
        advantage_score = 50
    else:
        advantage_score = 10

    strength = twin.swot["strengths"][0] if twin.swot["strengths"] else ""

    if strength and strength in str(Q4):
        alignment_score = 90
    else:
        alignment_score = 50

    if Q3b and comp_adv >= 70:
        objection_match = 90
    else:
        objection_match = 40

    positioning_score = (
        advantage_score * 0.5 +
        alignment_score * 0.3 +
        objection_match * 0.2
    )

    silo["positioning_score"] = positioning_score

    if positioning_score < 60:
        twin.insights.append(Insight(
            "Weak positioning — not addressing customer objections",
            "Rule 5.3",
            "HIGH"
        ))

    # =========================================================
    # RULE 5.4 — STP ALIGNMENT
    # =========================================================
    stp_alignment = (segmentation_score + targeting_score + positioning_score) / 3

    silo["stp_alignment"] = stp_alignment

    if stp_alignment < 60:
        twin.insights.append(Insight(
            "STP misalignment — unclear market focus",
            "Rule 5.4",
            "CRITICAL"
        ))

    # =========================================================
    # RULE 5.5 — ACQUISITION
    # =========================================================
    inbound_map = {
        "0-20": 10,
        "20-40": 30,
        "40-60": 50,
        "60-80": 70,
        "80-100": 90
    }

    inbound_mid = inbound_map.get(Q1, 30)

    total_channels = len(set(Q5 + Q6))

    if total_channels <= 4:
        penalty = 0
    elif total_channels <= 7:
        penalty = 0.2
    else:
        penalty = 0.5

        twin.insights.append(Insight(
            "Too many marketing channels — scattered effort",
            "Rule 5.5",
            "HIGH"
        ))

    social_score = 100 if Q2 == "Yes" else 0

    acquisition_score = (
        inbound_mid * 0.4 +
        social_score * 0.2 +
        (100 * (1 - penalty)) * 0.4
    )

    silo["acquisition_score"] = acquisition_score

    # =========================================================
    # RULE 5.6 — LEAD SOURCE BALANCE
    # =========================================================
    if inbound_mid >= 70:
        balance = "INBOUND"

    elif inbound_mid >= 40:
        balance = "BALANCED"

    else:
        balance = "OUTBOUND"

        twin.insights.append(Insight(
            "Over-reliance on outbound — weak brand pull",
            "Rule 5.6",
            "HIGH"
        ))

    silo["lead_balance"] = balance

    # =========================================================
    # RULE 5.7 — CHANNEL ALIGNMENT
    # =========================================================
    recommended = {
        "Captains": ["Networking", "Events"],
        "Engineers": ["Social", "SEO"],
        "Builders": ["Events", "Direct"],
        "Resellers": ["Email", "Networking"]
    }

    mismatch = False

    for a in Q4:
        if a in recommended:
            if not any(c in (Q5 + Q6) for c in recommended[a]):
                mismatch = True

    if mismatch:
        twin.insights.append(Insight(
            "Marketing channels not aligned with audience",
            "Rule 5.7",
            "HIGH"
        ))

    # =========================================================
    # RULE 5.8 — OBJECTION SEVERITY
    # =========================================================
    severity_map = {
        "Price": "HIGH",
        "Value": "HIGH",
        "Trust": "MEDIUM",
        "Competitor": "MEDIUM",
        "Timing": "MEDIUM",
        "Decision": "LOW",
        "Budget": "MEDIUM",
        "Logistics": "MEDIUM",
        "Product": "HIGH"
    }

    severity = severity_map.get(Q3b, "LOW")

    if severity == "HIGH":
        twin.insights.append(Insight(
            f"High severity objection: {Q3b}",
            "Rule 5.8",
            "HIGH"
        ))

    # =========================================================
    # RULE 5.9 — REVENUE SCORE (AARRR)
    # =========================================================
    recurring = twin.silos.get("financial", {}).get("business_model", "PROJECT")
    concentration = twin.silos.get("financial", {}).get("concentration_score", 50)
    repeat = 50  # placeholder until silo 6

    revenue_score = (
        (Q1 == "80-100") * 50 +
        concentration * 0.3 +
        repeat * 0.2
    )

    silo["revenue_score"] = revenue_score

    # =========================================================
    # RULE 5.10 — FUNNEL HEALTH
    # =========================================================
    retention = 50
    referral = 50

    if acquisition_score >= 70 and retention >= 70:
        funnel = "STRONG"

    elif acquisition_score >= 50:
        funnel = "MODERATE"

    elif acquisition_score < 40 or retention < 40:
        funnel = "WEAK"

        twin.insights.append(Insight(
            "Weak funnel — fix acquisition or retention",
            "Rule 5.10",
            "HIGH"
        ))

    else:
        funnel = "BROKEN"

        twin.insights.append(Insight(
            "Critical funnel breakdown",
            "Rule 5.10",
            "CRITICAL"
        ))

    silo["funnel_health"] = funnel

    # =========================================================
    # SAVE SILO
    # =========================================================
    twin.silos["marketing"] = silo