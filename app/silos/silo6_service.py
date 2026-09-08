from typing import Dict, Any


# =========================================================
# HELPERS
# =========================================================

def answer(
    data: Dict[str, Any],
    question_id: int,
    default=""
):
    """
    Return the answer for a numeric assessment question ID.

    The current backend passes answers in this format:

        {
            "38": "50-75%",
            "39": "2",
            "40": "3"
        }

    So this helper supports both string and integer keys.
    """

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
    """
    Convert a saved multi-select answer into a clean list.

    The frontend/backend currently stores multi-select values
    as comma-separated strings.
    """

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
    """
    Extract a leading numeric score.

    Examples:

        "2" -> 2
        "5 (Highly Consistent)" -> 5
        "3" -> 3
    """

    text = str(value or "").strip()

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
    """
    Convert the questionnaire's percentage ranges into
    approximate midpoints for comparative scoring.

    These are not treated as exact financial/customer values.
    They only represent the selected range.
    """

    text = (
        str(value or "")
        .strip()
        .replace("–", "-")
    )

    mappings = {
        "<25%": 12.5,
        "25-50%": 37.5,
        "50-75%": 62.5,
        ">75%": 87.5,

        "<10%": 5,
        "10-25%": 17.5,
        ">50%": 62.5,
    }

    return mappings.get(
        text,
        default
    )


# =========================================================
# RULE 6.1 — RELIABILITY
# =========================================================

def reliability(
    data: Dict[str, Any],
    silo3=None
):
    """
    Reliability is based only on directly relevant evidence:

    Q38:
        Percentage of repeat customers.

    Q39:
        Consistency of service/product quality.

    We do NOT calculate a SERVQUAL reliability dimension here,
    because the questionnaire does not collect the full
    expectation/perception dataset required for SERVQUAL.
    """

    quality = numeric_choice(
        answer(data, 39)
    )

    repeat_pct = percentage_midpoint(
        answer(data, 38)
    )

    if quality <= 0:
        return {
            "score": None,
            "quality_rating": None,
            "repeat_customer_range": str(
                answer(data, 38)
            ).strip(),
            "insight": (
                "Service consistency could not be scored "
                "because no valid quality rating was available."
            )
        }

    quality_score = (
        quality / 5
    ) * 100

    score = (
        quality_score * 0.65
        + repeat_pct * 0.35
    )

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 75:
        level = "STRONG"

    elif score >= 55:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "score": round(
            score,
            2
        ),
        "level": level,
        "quality_rating": quality,
        "repeat_customer_range": str(
            answer(data, 38)
        ).strip(),
        "alert": (
            "Service consistency requires attention"
            if score < 60
            else None
        )
    }


# =========================================================
# RULE 6.2 — ASSURANCE
# =========================================================

def assurance(
    data: Dict[str, Any],
    silo2=None
):
    """
    Assurance uses evidence related to expertise and
    dependency concentration.

    Q20:
        Percentage of core client relationships or technical
        expertise held by a single individual.

    Q41:
        What customers most frequently praise the company for.
    """

    praise_list = items(
        data,
        41
    )

    concentration = percentage_midpoint(
        answer(data, 20)
    )

    score = 50

    expertise_praise = any(
        (
            "expertise" in value.lower()
            or "knowledge" in value.lower()
        )
        for value in praise_list
    )

    quality_praise = any(
        "quality" in value.lower()
        for value in praise_list
    )

    reliability_praise = any(
        "reliability" in value.lower()
        for value in praise_list
    )

    if expertise_praise:
        score += 25

    elif quality_praise:
        score += 20

    elif reliability_praise:
        score += 15

    if concentration > 0:
        if concentration < 25:
            score += 15

        elif concentration >= 50:
            score -= 20

        elif concentration >= 25:
            score -= 5

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 75:
        level = "STRONG"

    elif score >= 55:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "score": round(
            score,
            2
        ),
        "level": level,
        "knowledge_concentration": str(
            answer(data, 20)
        ).strip(),
        "reported_praise": praise_list
    }


# =========================================================
# RULE 6.3 — TANGIBLES
# =========================================================

def tangibles(
    data: Dict[str, Any],
    silo3=None,
    silo5=None
):
    """
    The current assessment does NOT directly measure
    SERVQUAL tangibles such as:

    - physical facilities;
    - equipment appearance;
    - staff appearance;
    - customer-facing physical environment.

    Therefore no synthetic tangibles score is created.
    """

    return None


# =========================================================
# RULE 6.4 — EMPATHY
# =========================================================

def empathy(
    data: Dict[str, Any]
):
    """
    Empathy is inferred conservatively from customer
    praise and complaints.

    Q41:
        What customers praise.

    Q42:
        What customers complain about.

    This is not a formal SERVQUAL empathy score.
    """

    praise_list = items(
        data,
        41
    )

    complaint_list = items(
        data,
        42
    )

    score = 50

    positive_terms = (
        "customer service",
        "attention to detail",
        "going above",
        "above/beyond",
        "above and beyond",
        "flexibility",
        "professionalism"
    )

    negative_terms = (
        "communication",
        "lack of follow-up",
        "follow-up"
    )

    positive_signal = any(
        any(
            term in value.lower()
            for term in positive_terms
        )
        for value in praise_list
    )

    negative_signal = any(
        any(
            term in value.lower()
            for term in negative_terms
        )
        for value in complaint_list
    )

    if positive_signal:
        score += 25

    if negative_signal:
        score -= 25

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 75:
        level = "STRONG"

    elif score >= 55:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "score": round(
            score,
            2
        ),
        "level": level,
        "reported_praise": praise_list,
        "reported_complaints": complaint_list
    }


# =========================================================
# RULE 6.5 — RESPONSIVENESS
# =========================================================

def responsiveness(
    data: Dict[str, Any],
    silo3=None
):
    """
    Responsiveness is based on:

    Q40:
        Referral frequency.

    Q41:
        Praise for speed/responsiveness.

    Q42:
        Complaints about delays.

    It does not use arbitrary operational defaults.
    """

    referral = numeric_choice(
        answer(data, 40)
    )

    praise_list = items(
        data,
        41
    )

    complaint_list = items(
        data,
        42
    )

    referral_component = (
        referral / 5
    ) * 50 if referral else 0

    score = referral_component

    speed_praise = any(
        (
            "speed" in value.lower()
            or "responsiveness" in value.lower()
        )
        for value in praise_list
    )

    delay_complaint = any(
        "delay" in value.lower()
        for value in complaint_list
    )

    if speed_praise:
        score += 35

    else:
        score += 15

    if delay_complaint:
        score -= 20

    score = max(
        0,
        min(
            100,
            score
        )
    )

    if score >= 75:
        level = "STRONG"

    elif score >= 55:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "score": round(
            score,
            2
        ),
        "level": level,
        "referral_frequency": referral,
        "speed_praise_detected": speed_praise,
        "delay_complaint_detected": delay_complaint
    }


# =========================================================
# RULE 6.6 — SERVICE QUALITY INDEX
# =========================================================

def service_quality_index(
    data: Dict[str, Any],
    silo2=None,
    silo3=None
):
    """
    This is a Pulse assessment summary index.

    IMPORTANT:
    It is NOT labelled SERVQUAL because the questionnaire
    does not collect the complete SERVQUAL dataset.

    It combines only the service dimensions that the
    current questionnaire can reasonably support.
    """

    reliability_data = reliability(
        data,
        silo3
    )

    assurance_data = assurance(
        data,
        silo2
    )

    empathy_data = empathy(
        data
    )

    responsiveness_data = responsiveness(
        data,
        silo3
    )

    scores = []

    for result in [
        reliability_data,
        assurance_data,
        empathy_data,
        responsiveness_data
    ]:

        if not isinstance(
            result,
            dict
        ):
            continue

        value = result.get(
            "score"
        )

        if isinstance(
            value,
            (int, float)
        ):
            scores.append(
                float(value)
            )

    if not scores:
        return None

    score = (
        sum(scores)
        / len(scores)
    )

    if score >= 75:
        level = "STRONG"

    elif score >= 55:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "score": round(
            score,
            2
        ),
        "level": level,
        "dimensions_used": [
            "reliability",
            "assurance",
            "empathy",
            "responsiveness"
        ]
    }


# =========================================================
# RULE 6.7 — SERVQUAL
# =========================================================

def servqual(
    data: Dict[str, Any],
    silo2=None,
    silo3=None
):
    """
    Formal SERVQUAL cannot be calculated from the current
    assessment.

    SERVQUAL normally requires structured expectation and
    perception measurements across the dimensions.

    Returning None prevents a fabricated score from being
    treated as factual evidence.
    """

    return None


# =========================================================
# RULE 6.8 — CLV
# =========================================================

def clv(
    data: Dict[str, Any],
    silo4=None
):
    """
    Customer Lifetime Value cannot be calculated because
    the assessment does not collect the financial inputs
    required for a real CLV calculation, such as:

    - average order value;
    - purchase frequency;
    - gross margin;
    - acquisition cost;
    - customer lifespan;
    - churn.

    Do not manufacture a CLV score.
    """

    return None


# =========================================================
# RULE 6.9 — CLV IMPACT
# =========================================================

def clv_impact(
    clv_data,
    data: Dict[str, Any]
):
    """
    No CLV recommendation is produced when no valid CLV
    can be calculated.
    """

    return None


# =========================================================
# RULE 6.10 — RETENTION
# =========================================================

def retention(
    data: Dict[str, Any]
):
    """
    Retention uses the respondent's selected repeat-customer
    percentage range from Q38.
    """

    repeat_pct = percentage_midpoint(
        answer(data, 38)
    )

    reported_range = str(
        answer(data, 38)
    ).strip()

    if repeat_pct >= 75:
        level = "EXCELLENT"

    elif repeat_pct >= 50:
        level = "GOOD"

    elif repeat_pct >= 25:
        level = "FAIR"

    else:
        level = "LOW"

    return {
        "level": level,
        "reported_range": reported_range,
        "estimated_range_midpoint": repeat_pct
    }


# =========================================================
# RULE 6.11 — NPS
# =========================================================

def nps(
    data: Dict[str, Any]
):
    """
    Net Promoter Score cannot be calculated from Q40.

    Q40 asks:
        "How often do clients refer new business to you?"

    That is not the standard NPS question.

    Therefore returning a synthetic NPS number would be
    misleading.
    """

    return None


# =========================================================
# RULE 6.12 — CUSTOMER FEEDBACK SIGNALS
# =========================================================

def customer_feedback_signals(
    data: Dict[str, Any]
):
    """
    Preserve the actual customer feedback selected in the
    questionnaire without transforming it into unsupported
    metrics.
    """

    praise = items(
        data,
        41
    )

    complaints = items(
        data,
        42
    )

    return {
        "praise": praise,
        "complaints": complaints
    }


# =========================================================
# RULE 6.13 — REFERRAL SIGNAL
# =========================================================

def referral_signal(
    data: Dict[str, Any]
):
    """
    Q40 measures referral frequency on a 1–5 scale.
    Keep this as a referral-frequency signal rather than
    incorrectly converting it into NPS.
    """

    referral = numeric_choice(
        answer(data, 40)
    )

    if referral <= 0:
        return {
            "score": None,
            "level": "UNKNOWN"
        }

    if referral >= 4:
        level = "STRONG"

    elif referral == 3:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "score": referral,
        "scale": "1-5",
        "level": level
    }


# =========================================================
# RULE 6.14 — SERVICE CONSISTENCY
# =========================================================

def service_consistency(
    data: Dict[str, Any]
):
    """
    Preserve Q39 as its own direct service consistency
    measure.
    """

    rating = numeric_choice(
        answer(data, 39)
    )

    if rating <= 0:
        return {
            "rating": None,
            "level": "UNKNOWN"
        }

    if rating >= 4:
        level = "STRONG"

    elif rating == 3:
        level = "MODERATE"

    else:
        level = "WEAK"

    return {
        "rating": rating,
        "scale": "1-5",
        "level": level
    }


# =========================================================
# RULE 6.15 — SERVICE RISK SIGNALS
# =========================================================

def service_risk_signals(
    data: Dict[str, Any]
):
    """
    Produce only evidence-backed service risks.

    This function does not invent financial or statistical
    measurements.
    """

    risks = []

    repeat_pct = percentage_midpoint(
        answer(data, 38)
    )

    quality = numeric_choice(
        answer(data, 39)
    )

    referral = numeric_choice(
        answer(data, 40)
    )

    complaints = items(
        data,
        42
    )

    if repeat_pct and repeat_pct < 25:
        risks.append(
            "Repeat-customer rate is reported below 25%"
        )

    if quality and quality <= 2:
        risks.append(
            "Service or product consistency is rated low"
        )

    if referral and referral <= 2:
        risks.append(
            "Client referral frequency is low"
        )

    if any(
        "quality" in item.lower()
        for item in complaints
    ):
        risks.append(
            "Customers report quality-related complaints"
        )

    if any(
        "communication" in item.lower()
        for item in complaints
    ):
        risks.append(
            "Customers report communication-related complaints"
        )

    if any(
        "follow-up" in item.lower()
        for item in complaints
    ):
        risks.append(
            "Customers report follow-up issues"
        )

    if any(
        "consistency" in item.lower()
        for item in complaints
    ):
        risks.append(
            "Customers report consistency-related complaints"
        )

    if any(
        "delay" in item.lower()
        for item in complaints
    ):
        risks.append(
            "Customers report delays"
        )

    return risks


# =========================================================
# MAIN
# =========================================================

def run_silo6(
    data,
    silo2=None,
    silo3=None,
    silo4=None
):
    """
    Run the Service Quality silo using the CURRENT
    questionnaire schema.

    Current relevant question mapping:

        Q20
        Key-person concentration

        Q38
        Repeat customers

        Q39
        Service/product consistency

        Q40
        Referral frequency

        Q41
        Customer praise

        Q42
        Customer complaints

    Unsupported legacy metrics are deliberately returned
    as None rather than fabricated.
    """

    reliability_data = reliability(
        data,
        silo3
    )

    assurance_data = assurance(
        data,
        silo2
    )

    empathy_data = empathy(
        data
    )

    responsiveness_data = responsiveness(
        data,
        silo3
    )

    service_index = service_quality_index(
        data,
        silo2,
        silo3
    )

    retention_data = retention(
        data
    )

    referral_data = referral_signal(
        data
    )

    consistency_data = service_consistency(
        data
    )

    feedback = customer_feedback_signals(
        data
    )

    risks = service_risk_signals(
        data
    )

    return {
        "reliability": reliability_data,

        "assurance": assurance_data,

        # Not directly measured by current questionnaire.
        "tangibles": None,

        "empathy": empathy_data,

        "responsiveness": responsiveness_data,

        # Pulse-specific evidence-backed service summary.
        "service_quality_index": service_index,

        # Formal SERVQUAL cannot be calculated.
        "servqual": None,

        # Real CLV cannot be calculated.
        "clv": None,

        "clv_impact": None,

        "retention": retention_data,

        # Q40 is not an NPS question.
        "nps": None,

        "referral": referral_data,

        "service_consistency": consistency_data,

        "customer_feedback": feedback,

        "service_risks": risks,

        # Used by other silos as a broad retention signal.
        "repeat_score": percentage_midpoint(
            answer(data, 38)
        )
    }