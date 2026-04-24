from typing import Dict, Any, List, Optional

# =============================
# RULE 1.1 — STRATEGIC CLARITY
# =============================
def strategic_clarity(data):
    if data.q10_written_strategy == "Yes" and data.q9_employee_understanding in ["Yes", "Some"]:
        return {
            "level": "HIGH",
            "score": 90,
            "insight": "Clear documented strategy with team alignment"
        }

    if data.q10_written_strategy == "No" and data.q9_employee_understanding == "No":
        return {
            "level": "CRITICAL",
            "score": 20,
            "alert": "Major misalignment — no strategy and no team alignment"
        }

    return {
        "level": "MEDIUM",
        "score": 60,
        "insight": "Partial clarity — strategy or alignment is incomplete"
    }


# =============================
# RULE 1.2 — SHARED VALUES
# =============================
STRONG_DEFENSIBLE = [
    "Specialized expertise/knowledge",
    "Unique product/service offering",
    "Established relationships/network",
    "Technology/digital capabilities",
    "Brand reputation/heritage",
    "Superior quality/craftsmanship"
]

COMMODITY = [
    "Lower pricing than competitors",
    "Faster delivery/responsiveness",
    "Better customer service/support",
    "Geographic convenience/location"
]

NO_ADVANTAGE = "We don't have a clear competitive advantage"


def shared_values(data):
    selections = data.q5_competitive_advantage or []

    if NO_ADVANTAGE in selections:
        return {
            "score": 10,
            "strength": "WEAK",
            "insight": "No competitive differentiation identified"
        }

    strong = [s for s in selections if s in STRONG_DEFENSIBLE]
    commodity = [s for s in selections if s in COMMODITY]

    if len(strong) == 1 and not commodity:
        score = 90
        insight = "Clear and focused competitive advantage — strong shared values"

    elif 2 <= len(strong) <= 3 and not commodity:
        score = 70
        insight = "Multiple strong differentiators — good but risk of being unfocused"

    elif commodity and not strong:
        score = 50
        insight = "Competitive advantages are easy for competitors to replicate"

    elif strong and commodity:
        score = 65
        insight = "Strong differentiators diluted by commodity advantages"

    else:
        score = 50
        insight = "Unclear competitive positioning"

    if score >= 70 and data.q9_employee_understanding == "Yes":
        strength = "STRONG"
    elif score >= 70:
        strength = "MODERATE"
    else:
        strength = "WEAK"

    return {
        "score": score,
        "strength": strength,
        "insight": insight
    }


# =============================
# RULE 1.3 — STAFF ALIGNMENT
# =============================
def staff_alignment(data):
    score = 0

    # employee understanding
    if data.q9_employee_understanding == "Yes":
        score += 40
    elif data.q9_employee_understanding == "Some":
        score += 20

    # admin burden
    if data.q7_admin_percent < 30:
        score += 30
    elif data.q7_admin_percent < 50:
        score += 15

    # owner dependency
    if data.q12_owner_dependency == "No":
        score += 30
    elif data.q12_owner_dependency == "Some":
        score += 15

    return {
        "score": score,
        "status": "STRONG" if score >= 70 else "WEAK"
    }


# =============================
# RULE 1.4 — SYSTEMS
# =============================
def systems_efficiency(data):
    if data.q8_duplication == "A lot":
        return 50
    elif data.q8_duplication == "Some":
        return 75
    return 100


# =============================
# RULE 1.5 — SWOT STRENGTHS
# =============================
def swot_strengths(data, silo6=None):
    strengths = []

    strengths.append(data.q5_competitive_advantage)
    strengths.append(data.q7_strength)

    if data.q6_growth_confidence >= 4:
        strengths.append("Strong market position confidence")

    # Cross Silo (if available)
    if silo6:
        if data.q7_strength == "Our customer relationships" and silo6.get("repeat_pct", 0) >= 75:
            strengths.append("Strong customer loyalty")

        if data.q7_strength == "Our reputation/brand" and silo6.get("referral_freq", 0) >= 4:
            strengths.append("Strong brand advocacy")

    return strengths


# =============================
# RULE 1.6 — SWOT WEAKNESSES
# =============================
CHALLENGE_MAP = {
    "Finding and retaining good people": "Talent acquisition and retention weakness",
    "Managing cash flow": "Cash flow management weakness",
    "Operational inefficiencies/waste": "Operational inefficiency",
    "Lack of time for strategic work": "Leadership capacity constraint",
    "Regulatory/compliance requirements": "Compliance capability gap",
    "Generating consistent revenue/sales": "Revenue consistency weakness"
}


def swot_weaknesses(data):
    weaknesses = []

    if data.q7_admin_percent > 50:
        weaknesses.append("High administrative burden")

    if data.q8_duplication == "A lot":
        weaknesses.append("Process duplication")

    if data.q10_written_strategy == "No":
        weaknesses.append("Lack of strategic documentation")

    if data.q12_owner_dependency == "Yes":
        weaknesses.append("Owner dependency risk")

    challenge = getattr(data, "q9_biggest_challenge", None)

    if challenge in CHALLENGE_MAP:
        weaknesses.append(CHALLENGE_MAP[challenge])
    elif challenge:
        weaknesses.append(challenge)

    return weaknesses


# =============================
# RULE 1.7 — SWOT OPPORTUNITIES
# =============================
OPPORTUNITY_MAP = {
    "Expanding to new customer segments": "Market expansion opportunity",
    "New product/service offerings": "Product/service diversification",
    "Improving customer retention/upselling": "Revenue expansion from existing customers",
    "Digital marketing/online presence": "Digital channel growth",
    "Strategic partnerships/alliances": "Partnership-driven growth",
    "Technology/automation adoption": "Operational leverage through technology",
    "Developing recurring revenue streams": "Business model transformation to recurring revenue"
}


def swot_opportunities(data):
    ops = []

    for o in data.q11_growth_opportunities:
        ops.append(OPPORTUNITY_MAP.get(o, o))

    if data.q7_admin_percent > 40:
        ops.append("High ROI opportunity from automation")

    return ops


# =============================
# RULE 1.8 — SWOT THREATS
# =============================
def swot_threats(data):
    threats = []

    threats.extend(data.q3_competitors or [])

    if data.q9_employee_understanding == "No":
        threats.append("Strategic misalignment threatening execution")

    if data.q12_owner_dependency == "Yes":
        threats.append("Succession crisis risk")

    return threats


# =============================
# RULE 1.9 — 7S ALIGNMENT
# =============================
def seven_s_alignment(data, silo2=None, silo3=None):
    scores = []

    # Strategy
    scores.append(90 if data.q10_written_strategy == "Yes" else 40)

    # Systems
    scores.append(systems_efficiency(data))

    # Shared Values
    scores.append(shared_values(data)["score"])

    # Staff
    scores.append(staff_alignment(data)["score"])

    # Structure (from Silo 3 if available)
    scores.append(silo3.get("structure", 60) if silo3 else 60)

    # Style (based on leadership issues proxy)
    scores.append(40 if data.q9_employee_understanding == "No" else 70)

    # Skills (from Silo 2)
    scores.append(silo2.get("skills", 60) if silo2 else 60)

    avg = sum(scores) / len(scores)

    return {
        "score": avg,
        "alert": "Critical 7S Misalignment Detected" if avg < 60 else None
    }


# =============================
# RULE 1.10 — GROWTH REALITY CHECK
# =============================
def growth_check(data, silo7=None):
    warnings = []

    if data.q6_growth_confidence >= 4:

        if data.q10_written_strategy == "No":
            warnings.append("Growth confidence not supported by strategy")

        if data.q9_employee_understanding == "No":
            warnings.append("Team not aligned with growth strategy")

        if data.q12_owner_dependency == "Yes":
            warnings.append("Owner dependency limits scalability")

    # Capital constraint
    capital_intensive = [
        "Geographic expansion",
        "Acquiring competitors/businesses",
        "New product/service offerings"
    ]

    if silo7:
        runway = silo7.get("runway_months", 12)

        if any(x in data.q11_growth_opportunities for x in capital_intensive) and runway < 6:
            warnings.append("Growth strategy requires capital not currently available")

    return warnings


# =============================
# MAIN
# =============================
def run_silo1(data, silo2=None, silo3=None, silo6=None, silo7=None):
    return {
        "strategic_clarity": strategic_clarity(data),
        "shared_values": shared_values(data),
        "staff_alignment": staff_alignment(data),
        "systems_efficiency": systems_efficiency(data),
        "swot": {
            "strengths": swot_strengths(data, silo6),
            "weaknesses": swot_weaknesses(data),
            "opportunities": swot_opportunities(data),
            "threats": swot_threats(data)
        },
        "seven_s": seven_s_alignment(data, silo2, silo3),
        "growth_warnings": growth_check(data, silo7)
    }