from typing import Dict, Any, List


# =========================================================
# HELPERS
# =========================================================

def answer(
    data: Dict[str, Any],
    question_id: int,
    default=""
):
    value = data.get(
        str(question_id),
        data.get(question_id, default)
    )

    if value is None:
        return default

    return value


def items(
    data: Dict[str, Any],
    question_id: int
):
    value = answer(
        data,
        question_id,
        []
    )

    if isinstance(value, list):
        return [
            str(item).strip()
            for item in value
            if str(item).strip()
        ]

    if not value:
        return []

    return [
        item.strip()
        for item in str(value).split(",")
        if item.strip()
    ]


def numeric_choice(
    value,
    default=0
):
    text = str(
        value or ""
    ).strip()

    if not text:
        return default

    try:
        return int(
            text.split()[0]
        )

    except Exception:
        return default


def percentage_midpoint(
    value,
    default=0
):
    text = (
        str(value or "")
        .strip()
        .replace("–", "-")
        .replace("—", "-")
    )

    mappings = {
        "<5%": 2.5,
        "5-15%": 10,
        "15-25%": 20,
        "25-50%": 37.5,
        "50-75%": 62.5,
        ">75%": 87.5,

        "<10%": 5,
        "10-25%": 17.5,
        ">50%": 62.5,

        "<25%": 12.5,

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

    if text in mappings:
        return mappings[text]

    if "25-50" in text:
        return 37.5

    if "50-75" in text:
        return 62.5

    if ">75" in text:
        return 87.5

    if ">50" in text:
        return 62.5

    if "<25" in text:
        return 12.5

    return default


def runway_band(
    value
):
    text = (
        str(value or "")
        .strip()
        .replace("–", "-")
        .replace("—", "-")
        .lower()
    )

    if "<3" in text:
        return "<3"

    if "3-6" in text:
        return "3-6"

    if "6-12" in text:
        return "6-12"

    if ">12" in text:
        return ">12"

    return None


def sop_is_weak(
    value
):
    text = str(
        value or ""
    ).strip().lower()

    if not text:
        return False

    return (
        text == "no"
        or text == "none"
        or "some" in text
        or "informal" in text
    )


def owner_dependency_is_high(
    value
):
    text = str(
        value or ""
    ).strip().lower()

    return (
        "heavily owner-dependent" in text
        or "highly owner-dependent" in text
        or "cannot operate" in text
    )


def add_unique(
    collection: List[str],
    message: str
):
    message = str(
        message or ""
    ).strip()

    if (
        message
        and message not in collection
    ):
        collection.append(
            message
        )


def add_insight(
    insights: List[str],
    message: str
):
    add_unique(
        insights,
        message
    )


def add_recommendation(
    recommendations: List[str],
    message: str
):
    add_unique(
        recommendations,
        message
    )


def add_risk(
    risks: List[Dict[str, str]],
    level: str,
    message: str,
    category: str = "CROSS_SILO"
):
    level = str(
        level or ""
    ).strip().upper()

    message = str(
        message or ""
    ).strip()

    category = str(
        category or "CROSS_SILO"
    ).strip().upper()

    if not message:
        return

    candidate = {
        "level": level,
        "category": category,
        "message": message
    }

    if candidate not in risks:
        risks.append(
            candidate
        )


# =========================================================
# CS.1 — STRATEGY ↔ PEOPLE
# =========================================================

def cs1(
    data,
    s1,
    s2,
    insights,
    recommendations,
    risks
):
    written_strategy = str(
        answer(data, 11)
    ).strip()

    employee_understanding = str(
        answer(data, 10)
    ).strip()

    if (
        written_strategy == "Yes"
        and employee_understanding == "No"
    ):
        add_insight(
            insights,
            (
                "A written strategy exists, but employees report "
                "that they do not understand the company's goals "
                "and direction."
            )
        )

        add_recommendation(
            recommendations,
            (
                "Translate the written strategy into clear team-level "
                "priorities and communicate how individual roles "
                "support those priorities."
            )
        )

    knowledge_concentration = percentage_midpoint(
        answer(data, 20)
    )

    if (
        owner_dependency_is_high(
            answer(data, 13)
        )
        and knowledge_concentration > 50
    ):
        add_risk(
            risks,
            "HIGH",
            (
                "Business continuity is exposed because the company "
                "is heavily dependent on the owner or key leader while "
                "more than half of critical relationships or expertise "
                "are concentrated in one individual."
            ),
            "STRATEGIC"
        )

        add_recommendation(
            recommendations,
            (
                "Prioritise succession planning and transfer critical "
                "relationships and knowledge to additional people."
            )
        )


# =========================================================
# CS.2 — STRATEGY ↔ OPERATIONS
# =========================================================

def cs2(
    data,
    s1,
    s3,
    insights,
    recommendations
):
    written_strategy = str(
        answer(data, 11)
    ).strip()

    sops = answer(
        data,
        21
    )

    if (
        written_strategy == "Yes"
        and sop_is_weak(sops)
    ):
        add_insight(
            insights,
            (
                "The business has a written strategy, but process "
                "documentation is incomplete, creating an execution gap."
            )
        )

        add_recommendation(
            recommendations,
            (
                "Convert strategic priorities into documented operating "
                "processes for the activities most important to execution."
            )
        )

    admin_percent = percentage_midpoint(
        answer(data, 8)
    )

    automation = str(
        answer(data, 23)
    ).strip()

    if (
        admin_percent > 50
        and automation == "No"
    ):
        add_insight(
            insights,
            (
                "A high share of leadership time is spent on administration "
                "while automation is not currently in use."
            )
        )

        add_recommendation(
            recommendations,
            (
                "Evaluate the highest-volume administrative activities "
                "for workflow simplification or automation."
            )
        )


# =========================================================
# CS.3 — STRATEGY ↔ FINANCIAL RESILIENCE
# =========================================================

def cs3(
    data,
    s4,
    s7,
    insights,
    recommendations,
    risks
):
    growth_confidence = numeric_choice(
        answer(data, 7)
    )

    runway = runway_band(
        answer(data, 48)
    )

    if (
        growth_confidence >= 4
        and runway in {
            "<3",
            "3-6"
        }
    ):
        add_risk(
            risks,
            "HIGH",
            (
                "High confidence in growth is combined with a reported "
                "operational runway of six months or less."
            ),
            "FINANCIAL"
        )

        add_recommendation(
            recommendations,
            (
                "Stress-test growth plans against available cash runway "
                "before committing to material expansion costs."
            )
        )

    concentration = percentage_midpoint(
        answer(data, 28)
    )

    if concentration >= 50:
        add_recommendation(
            recommendations,
            (
                "Reduce dependence on the largest customer before "
                "increasing fixed commitments associated with growth."
            )
        )


# =========================================================
# CS.4 — PEOPLE ↔ SERVICE
# =========================================================

def cs4(
    data,
    s2,
    s3,
    s6,
    insights,
    recommendations,
    risks
):
    turnover = percentage_midpoint(
        answer(data, 18)
    )

    if turnover >= 50:
        add_risk(
            risks,
            "HIGH",
            (
                "High employee turnover creates a continuity risk "
                "for service delivery and organisational knowledge."
            ),
            "PEOPLE"
        )

        add_recommendation(
            recommendations,
            (
                "Address the reported drivers of employee performance "
                "and retention before materially increasing delivery complexity."
            )
        )

    roles = str(
        answer(data, 16)
    ).strip()

    sops = answer(
        data,
        21
    )

    if (
        roles == "No"
        and sop_is_weak(sops)
    ):
        add_risk(
            risks,
            "HIGH",
            (
                "Role responsibilities and operating procedures are both "
                "insufficiently defined, increasing execution inconsistency."
            ),
            "OPERATIONS"
        )

        add_recommendation(
            recommendations,
            (
                "Define ownership, responsibilities and minimum SOPs "
                "for critical recurring activities."
            )
        )


# =========================================================
# CS.5 — KNOWLEDGE CONCENTRATION
# =========================================================

def cs5(
    data,
    s2,
    s6,
    insights,
    recommendations,
    risks
):
    concentration = percentage_midpoint(
        answer(data, 20)
    )

    turnover = percentage_midpoint(
        answer(data, 18)
    )

    if (
        concentration >= 25
        and turnover >= 25
    ):
        add_risk(
            risks,
            "HIGH",
            (
                "Material knowledge concentration is combined with elevated "
                "employee turnover, increasing exposure to knowledge loss."
            ),
            "PEOPLE"
        )

        add_recommendation(
            recommendations,
            (
                "Document critical expertise and relationships and cross-train "
                "additional employees in the highest-dependency areas."
            )
        )

    service_index = (
        s6.get(
            "service_quality_index"
        )
        if isinstance(
            s6,
            dict
        )
        else None
    )

    service_score = (
        service_index.get("score")
        if isinstance(
            service_index,
            dict
        )
        else None
    )

    if (
        concentration > 50
        and isinstance(
            service_score,
            (int, float)
        )
        and service_score >= 75
    ):
        add_insight(
            insights,
            (
                "Service performance is currently strong while critical "
                "expertise or relationships are highly concentrated, "
                "creating a key-person dependency risk."
            )
        )


# =========================================================
# CS.6 — OPERATIONAL EFFICIENCY SIGNALS
# =========================================================

def cs6(
    data,
    s1,
    s2,
    s3,
    s4,
    insights,
    recommendations
):
    signals = []

    if sop_is_weak(
        answer(data, 21)
    ):
        signals.append(
            "incomplete process documentation"
        )

    if str(
        answer(data, 9)
    ).strip() == "A lot":
        signals.append(
            "significant duplication"
        )

    severity = str(
        answer(data, 5)
    ).strip().lower()

    if (
        "critical" in severity
        or "major" in severity
    ):
        signals.append(
            "a high-impact operational bottleneck"
        )

    if percentage_midpoint(
        answer(data, 18)
    ) >= 50:
        signals.append(
            "high employee turnover"
        )

    if (
        str(
            answer(data, 23)
        ).strip() == "No"
        and percentage_midpoint(
            answer(data, 8)
        ) > 50
    ):
        signals.append(
            "high administrative workload without automation"
        )

    if str(
        answer(data, 29)
    ).strip() == "Yes":
        signals.append(
            "suspected financial waste"
        )

    if len(signals) >= 3:
        add_insight(
            insights,
            (
                "Multiple efficiency warning signals are present: "
                + ", ".join(signals)
                + "."
            )
        )

        add_recommendation(
            recommendations,
            (
                "Prioritise the reported operational bottleneck and "
                "process duplication before adding further complexity."
            )
        )


# =========================================================
# CS.7 — MARKETING ↔ RETENTION
# =========================================================

def cs7(
    data,
    s5,
    s6,
    insights,
    recommendations
):
    acquisition_data = (
        s5.get("acquisition")
        if isinstance(
            s5,
            dict
        )
        else None
    )

    acquisition = (
        acquisition_data.get("score")
        if isinstance(
            acquisition_data,
            dict
        )
        else None
    )

    repeat_customers = percentage_midpoint(
        answer(data, 38)
    )

    if (
        isinstance(
            acquisition,
            (int, float)
        )
        and acquisition >= 70
        and repeat_customers < 50
    ):
        add_insight(
            insights,
            (
                "Acquisition capability is relatively strong while "
                "repeat-customer levels remain below 50%, indicating "
                "an acquisition-retention imbalance."
            )
        )

        add_recommendation(
            recommendations,
            (
                "Investigate the customer experience after acquisition "
                "and prioritise the causes of weak repeat business."
            )
        )

    referral = numeric_choice(
        answer(data, 40)
    )

    lead_balance = (
        s5.get("lead_balance")
        if isinstance(
            s5,
            dict
        )
        else None
    )

    if (
        referral >= 4
        and lead_balance != "INBOUND_DOMINANT"
    ):
        add_recommendation(
            recommendations,
            (
                "Build a more deliberate referral process around the "
                "existing strong referral signal."
            )
        )


# =========================================================
# CS.8 — SERVICE ↔ FINANCIAL EXPOSURE
# =========================================================

def cs8(
    data,
    s4,
    s6,
    insights,
    recommendations,
    risks
):
    repeat_customers = percentage_midpoint(
        answer(data, 38)
    )

    if repeat_customers >= 75:
        add_insight(
            insights,
            (
                "The reported repeat-customer range is high, providing "
                "a positive customer-retention signal."
            )
        )

    quality = numeric_choice(
        answer(data, 39)
    )

    concentration = percentage_midpoint(
        answer(data, 28)
    )

    if (
        quality > 0
        and quality <= 2
        and concentration >= 50
    ):
        add_risk(
            risks,
            "HIGH",
            (
                "Low service consistency is combined with high customer "
                "revenue concentration, increasing exposure if a major "
                "customer relationship deteriorates."
            ),
            "COMMERCIAL"
        )

        add_recommendation(
            recommendations,
            (
                "Address the causes of low service consistency and reduce "
                "dependence on the largest customer."
            )
        )


# =========================================================
# CS.9 — DIGITAL CAPABILITY ↔ STRATEGY
# =========================================================

def cs9(
    s1,
    s3,
    insights
):
    quadrant = (
        s3.get("quadrant")
        if isinstance(
            s3,
            dict
        )
        else None
    )

    if quadrant == "DIGIRATI":
        add_insight(
            insights,
            (
                "The assessment indicates relatively strong digital "
                "capability and transformation management, which can "
                "support strategic execution."
            )
        )

    elif quadrant == "BEGINNERS":
        add_insight(
            insights,
            (
                "The assessment indicates low digital capability and "
                "weak transformation management, which may constrain "
                "operational scalability."
            )
        )


# =========================================================
# CS.10 — ENTERPRISE RISK
# =========================================================

def cs10(
    s7,
    insights,
    recommendations
):
    enterprise = (
        s7.get(
            "enterprise_risk"
        )
        if isinstance(
            s7,
            dict
        )
        else None
    )

    if not isinstance(
        enterprise,
        dict
    ):
        return

    level = str(
        enterprise.get(
            "level"
        )
        or ""
    ).upper()

    if level in {
        "HIGH",
        "CRITICAL"
    }:
        add_recommendation(
            recommendations,
            (
                "Prioritise the specific control, continuity and "
                "concentration risks contributing to enterprise risk."
            )
        )


# =========================================================
# CS.12 — ACQUISITION ↔ RETENTION
# =========================================================

def cs12(
    s4,
    s5,
    s6,
    insights,
    recommendations
):
    acquisition_data = (
        s5.get("acquisition")
        if isinstance(
            s5,
            dict
        )
        else None
    )

    acquisition = (
        acquisition_data.get("score")
        if isinstance(
            acquisition_data,
            dict
        )
        else None
    )

    retention = (
        s6.get("repeat_score")
        if isinstance(
            s6,
            dict
        )
        else None
    )

    stages = []

    if isinstance(
        acquisition,
        (int, float)
    ):
        stages.append(
            (
                "Acquisition",
                float(acquisition)
            )
        )

    if isinstance(
        retention,
        (int, float)
    ):
        stages.append(
            (
                "Retention",
                float(retention)
            )
        )

    if len(stages) < 2:
        return

    weakest = min(
        stages,
        key=lambda item: item[1]
    )

    strongest = max(
        stages,
        key=lambda item: item[1]
    )

    if (
        strongest[1]
        - weakest[1]
    ) >= 15:
        add_insight(
            insights,
            (
                f"{weakest[0]} is materially weaker than "
                f"{strongest[0]} in the available commercial signals."
            )
        )

        add_recommendation(
            recommendations,
            (
                f"Prioritise the causes of weaker {weakest[0].lower()} "
                "performance before attempting to scale the stronger stage."
            )
        )


# =========================================================
# CS.14 — CLV : CAC
# =========================================================

def cs14(
    s6,
    s5,
    insights,
    recommendations,
    risks
):
    """
    Intentionally disabled.

    The current assessment does not collect the financial
    inputs required to calculate real CLV or CAC.

    Therefore no CLV:CAC ratio or unit-economics conclusion
    may be generated.
    """

    return


# =========================================================
# CS.16 — DIGITAL IMPROVEMENT OPPORTUNITY
# =========================================================

def cs16(
    data,
    s3,
    s4,
    insights,
    recommendations
):
    quadrant = (
        s3.get("quadrant")
        if isinstance(
            s3,
            dict
        )
        else None
    )

    suspected_waste = str(
        answer(data, 29)
    ).strip()

    if (
        quadrant in {
            "BEGINNERS",
            "CONSERVATIVES"
        }
        and suspected_waste == "Yes"
    ):
        add_recommendation(
            recommendations,
            (
                "Assess whether the reported areas of financial waste "
                "overlap with manual or inefficient processes before "
                "selecting automation investments."
            )
        )


# =========================================================
# PRIORITIES ENGINE
# =========================================================

def priorities(
    insights,
    risks
):
    level_order = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3
    }

    ordered = sorted(
        risks,
        key=lambda item: level_order.get(
            str(
                item.get("level")
                or ""
            ).upper(),
            99
        )
    )

    result = []

    for item in ordered:
        message = str(
            item.get("message")
            or ""
        ).strip()

        if (
            message
            and message not in result
        ):
            result.append(
                message
            )

        if len(result) >= 5:
            break

    return result


# =========================================================
# MAIN
# =========================================================

def run_cross_analysis(
    data,
    silo1,
    silo2,
    silo3,
    silo4,
    silo5,
    silo6,
    silo7
):
    insights: List[str] = []
    recommendations: List[str] = []
    risks: List[Dict[str, str]] = []

    cs1(
        data,
        silo1,
        silo2,
        insights,
        recommendations,
        risks
    )

    cs2(
        data,
        silo1,
        silo3,
        insights,
        recommendations
    )

    cs3(
        data,
        silo4,
        silo7,
        insights,
        recommendations,
        risks
    )

    cs4(
        data,
        silo2,
        silo3,
        silo6,
        insights,
        recommendations,
        risks
    )

    cs5(
        data,
        silo2,
        silo6,
        insights,
        recommendations,
        risks
    )

    cs6(
        data,
        silo1,
        silo2,
        silo3,
        silo4,
        insights,
        recommendations
    )

    cs7(
        data,
        silo5,
        silo6,
        insights,
        recommendations
    )

    cs8(
        data,
        silo4,
        silo6,
        insights,
        recommendations,
        risks
    )

    cs9(
        silo1,
        silo3,
        insights
    )

    cs10(
        silo7,
        insights,
        recommendations
    )

    cs12(
        silo4,
        silo5,
        silo6,
        insights,
        recommendations
    )

    cs14(
        silo6,
        silo5,
        insights,
        recommendations,
        risks
    )

    cs16(
        data,
        silo3,
        silo4,
        insights,
        recommendations
    )

    return {
        "insights": insights,
        "recommendations": recommendations,
        "risks": risks,
        "top_priorities": priorities(
            insights,
            risks
        )
    }