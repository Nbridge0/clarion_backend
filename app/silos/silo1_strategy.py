from typing import Dict, Any


def answer(data: Dict[str, Any], question_id: int, default=""):
    value = data.get(str(question_id), data.get(question_id, default))
    return value if value is not None else default


def items(data: Dict[str, Any], question_id: int):
    value = answer(data, question_id, [])

    if isinstance(value, list):
        return [str(x).strip() for x in value if str(x).strip()]

    if not value:
        return []

    return [
        x.strip()
        for x in str(value).split(",")
        if x.strip()
    ]


def range_midpoint(value, default=0):
    text = str(value or "").strip().replace("–", "-")

    mapping = {
        "0-10%": 5,
        "10-20%": 15,
        "20-30%": 25,
        "30-40%": 35,
        "40-50%": 45,
        "50-60%": 55,
        "60-70%": 65,
        "70-80%": 75,
        "80-90%": 85,
        "90-100%": 95,
    }

    return mapping.get(text, default)


def numeric_choice(value, default=0):
    text = str(value or "").strip()

    try:
        return int(text.split()[0])
    except Exception:
        return default


def strategic_clarity(data):
    employee_understanding = str(answer(data, 10)).strip()
    written_strategy = str(answer(data, 11)).strip()

    if written_strategy == "Yes" and employee_understanding == "Yes":
        return {
            "level": "HIGH",
            "score": 90,
            "insight": "Documented strategy with clear employee understanding"
        }

    if written_strategy == "No" and employee_understanding == "No":
        return {
            "level": "CRITICAL",
            "score": 20,
            "alert": "No written strategy and employees do not understand company direction"
        }

    if written_strategy == "No":
        return {
            "level": "MEDIUM",
            "score": 50,
            "insight": "Strategic direction exists without a written strategy"
        }

    return {
        "level": "MEDIUM",
        "score": 65,
        "insight": "Strategy exists but company-wide understanding is incomplete"
    }


def shared_values(data):
    advantages = items(data, 2)

    if not advantages:
        return {
            "score": None,
            "strength": "UNKNOWN",
            "insight": "No competitive advantage evidence supplied"
        }

    no_advantage = any(
        "no clear advantage" in x.lower()
        or "don't have a clear competitive advantage" in x.lower()
        for x in advantages
    )

    if no_advantage:
        return {
            "score": 20,
            "strength": "WEAK",
            "insight": "No clear competitive differentiation identified"
        }

    defensible_terms = (
        "expertise",
        "quality",
        "technology",
        "unique",
        "network",
        "reputation",
        "brand"
    )

    defensible_count = sum(
        1
        for value in advantages
        if any(term in value.lower() for term in defensible_terms)
    )

    if defensible_count >= 2:
        score = 80
        strength = "STRONG"
        insight = "Multiple defensible competitive strengths are identified"

    elif defensible_count == 1:
        score = 70
        strength = "MODERATE"
        insight = "At least one defensible competitive strength is identified"

    else:
        score = 55
        strength = "MODERATE"
        insight = "Competitive advantages are identified but differentiation may be easier to replicate"

    return {
        "score": score,
        "strength": strength,
        "insight": insight
    }


def staff_alignment(data):
    understanding = str(answer(data, 10)).strip()
    admin_percent = range_midpoint(answer(data, 8))
    dependency = str(answer(data, 13)).strip().lower()

    score = 0

    if understanding == "Yes":
        score += 40
    elif understanding == "Some":
        score += 20

    if admin_percent and admin_percent < 30:
        score += 30
    elif admin_percent and admin_percent < 50:
        score += 15

    if "fully autonomous" in dependency:
        score += 30
    elif "minor friction" in dependency:
        score += 20

    return {
        "score": score,
        "status": (
            "STRONG"
            if score >= 70
            else "MODERATE"
            if score >= 50
            else "WEAK"
        )
    }


def systems_efficiency(data):
    duplication = str(answer(data, 9)).strip()

    if duplication == "A lot":
        return 40

    if duplication == "Some":
        return 70

    if duplication == "None":
        return 100

    return None


def swot_strengths(data):
    result = []

    for value in items(data, 3) + items(data, 2):
        if value not in result:
            result.append(value)

    if numeric_choice(answer(data, 7)) >= 4:
        result.append("High confidence in sustainable growth")

    return result


def swot_weaknesses(data):
    result = []

    for value in items(data, 4):
        if "no significant bottleneck" not in value.lower():
            result.append(value)

    for value in items(data, 6):
        if value not in result:
            result.append(value)

    if str(answer(data, 11)).strip() == "No":
        result.append("No written business strategy or growth plan")

    dependency = str(answer(data, 13)).lower()

    if "heavily owner-dependent" in dependency:
        result.append("Heavy dependency on the owner or key leader")

    return result


def swot_opportunities(data):
    result = list(items(data, 12))

    admin_percent = range_midpoint(answer(data, 8))

    if admin_percent > 40:
        result.append(
            "Potential to release leadership capacity through process improvement or automation"
        )

    return result


def swot_threats(data):
    threats = []

    if str(answer(data, 10)).strip() == "No":
        threats.append(
            "Employees do not understand the company's goals and direction"
        )

    if "heavily owner-dependent" in str(answer(data, 13)).lower():
        threats.append(
            "Business continuity depends heavily on the owner or key leader"
        )

    severity = str(answer(data, 5)).lower()

    if "critical" in severity or "major" in severity:
        threats.append(
            "The reported primary operational bottleneck has a major business impact"
        )

    return threats


def seven_s_alignment(data, silo2=None, silo3=None):
    # Do not manufacture a McKinsey 7S score without all seven dimensions.
    return None


def growth_check(data, silo7=None):
    warnings = []

    confidence = numeric_choice(answer(data, 7))

    if confidence >= 4:
        if str(answer(data, 11)).strip() == "No":
            warnings.append(
                "High growth confidence is not supported by a written strategy"
            )

        if str(answer(data, 10)).strip() == "No":
            warnings.append(
                "Growth ambition may be constrained by weak employee alignment"
            )

        if "heavily owner-dependent" in str(answer(data, 13)).lower():
            warnings.append(
                "Owner dependency may constrain scalability"
            )

    return warnings


def run_silo1(data, silo2=None, silo3=None, silo6=None, silo7=None):
    return {
        "strategic_clarity": strategic_clarity(data),
        "shared_values": shared_values(data),
        "staff_alignment": staff_alignment(data),
        "systems_efficiency": systems_efficiency(data),
        "swot": {
            "strengths": swot_strengths(data),
            "weaknesses": swot_weaknesses(data),
            "opportunities": swot_opportunities(data),
            "threats": swot_threats(data)
        },
        "seven_s": seven_s_alignment(data, silo2, silo3),
        "growth_warnings": growth_check(data, silo7)
    }