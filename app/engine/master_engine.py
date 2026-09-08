from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor, as_completed

import os
import json

from openai import OpenAI

from app.silos.silo1_strategy import run_silo1
from app.silos.silo2_hr import run_silo2
from app.silos.silo3_efficiency import run_silo3
from app.silos.silo4_financial import run_silo4
from app.silos.silo5_marketing import run_silo5
from app.silos.silo6_service import run_silo6
from app.silos.silo7_risk import run_silo7

from app.cross.cross_rules import run_cross_analysis


# =========================================================
# OPENAI CONFIGURATION
# =========================================================

OPENAI_API_KEY = os.getenv(
    "OPENAI_API_KEY"
)

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing from the backend environment."
    )


OPENAI_ANALYSIS_MODEL = os.getenv(
    "OPENAI_ANALYSIS_MODEL",
    "gpt-4.1-mini"
)


openai_client = OpenAI(
    api_key=OPENAI_API_KEY,
    timeout=30.0,
    max_retries=2
)


# =========================================================
# CURRENT ASSESSMENT QUESTION SCHEMA
# =========================================================
#
# This is schema metadata, not hard-coded business analysis.
#
# It tells the intelligence layer what each persisted numeric
# answer ID actually means.
#
# =========================================================

QUESTION_LABELS = {
    1: "Main business priorities for the next 12-24 months",
    2: "Main competitive advantages",
    3: "Main business strengths",
    4: "Primary operational bottlenecks",
    5: "Severity or business impact of the primary bottleneck",
    6: "Main challenges faced by the owner or key leader",
    7: "Confidence in sustainable growth",
    8: "Percentage of owner or leadership time spent on administration versus higher-value work",
    9: "Level of duplicated work or duplicated processes",
    10: "Whether employees understand the company's goals and direction",
    11: "Whether the business has a written strategy or growth plan",
    12: "Main growth opportunities",
    13: "Ability of the business to operate without the owner or key leader for six months",

    14: "Number of employees",
    15: "Departments or functional areas",
    16: "Whether roles have clear job descriptions and KPIs",
    17: "Whether employee satisfaction or engagement is measured",
    18: "Employee turnover range",
    19: "What would most improve employee performance",
    20: "Percentage of critical client relationships or technical expertise concentrated in one individual",

    21: "Extent to which important processes are documented as SOPs",
    22: "Whether the business has adequate software and systems",
    23: "Whether automation is currently used",
    24: "Whether the business has experimented with AI",
    25: "Business areas where AI could improve performance",
    26: "Self-assessed AI or digital readiness",
    27: "Availability of pre-vetted Tier-2 alternative suppliers or vendors",

    28: "Revenue concentration represented by the largest customer",
    29: "Whether the business suspects areas of financial waste",
    30: "Percentage of revenue that is recurring",

    31: "Percentage of leads or sales generated inbound",
    32: "Whether the business actively uses social media",
    33: "Primary target customer segments",
    34: "Main customer buying objections",
    35: "Clarity on why customers choose the business",
    36: "Lead-generation channels",
    37: "Marketing channels",

    38: "Percentage of customers that are repeat customers",
    39: "Consistency of product or service quality",
    40: "Frequency with which customers refer new business",
    41: "What customers most frequently praise",
    42: "What customers most frequently complain about",

    43: "Whether subcontractors must provide proof of insurance",
    44: "How sanctions screening is performed",
    45: "How ultimate beneficial ownership is verified",
    46: "Whether Professional Indemnity insurance covers the largest contract",
    47: "Whether the business has a policy for referral fees",
    48: "Operational cash runway"
}

# =========================================================
# SILO EVIDENCE SCOPE
# =========================================================
# Which questions each silo is actually allowed to analyse.

SILO_EVIDENCE_QUESTION_IDS = {
    "strategy": {
        1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11, 12, 13
    },

    "people": {
        10,
        14, 15, 16, 17, 18, 19, 20
    },

    "operations": {
        4, 5, 8, 9, 10, 11,
        21, 22, 23, 24, 25, 26, 27, 29
    },

    "financial": {
        28, 29, 30, 48
    },

    "marketing": {
        2,
        31, 32, 33, 34, 35, 36, 37, 38
    },

    "service": {
        20,
        38, 39, 40, 41, 42
    },

    "risk": {
        13, 18, 20, 27,
        28, 29, 30, 38, 40,
        43, 44, 45, 46, 47, 48
    }
}


# =========================================================
# SILO UPDATE DEPENDENCIES
# =========================================================

QUESTION_UPDATE_SILO_IDS = {

    "strategy": {
        # Direct Strategy
        1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11, 12, 13,

        # Rule 3.9
        21,

        # CS.22
        14, 18,

        # Finance Rule 4.2
        28
    },

    "people": {
        # Direct People
        10,
        14, 15, 16, 17, 18, 19, 20,

        # Rule 3.9
        21
    },

    "operations": {
        # Direct Operations
        4, 5, 8, 9, 10, 11,
        21, 22, 23, 24, 25, 26, 27, 29,

        # CS.4 — turnover affects process stability
        18
    },

    "financial": {
        # Direct Financial
        28, 29, 30, 48,

        # Rule 4.6
        8, 21,

        # Rules 4.7 / 4.8
        14, 22, 23, 24, 26,

        # CS.6
        5, 9, 18
    },

    "marketing": {
        # Direct Marketing
        2,
        31, 32, 33, 34, 35, 36, 37, 38,

        # CS.22
        12, 14, 18, 20,

        # Finance Rule 4.2
        28
    },

    "service": {
        # Direct Service
        20,
        38, 39, 40, 41, 42,

        # Rule 3.9
        21,

        # CS.4
        18
    },

    "risk": {
        # Existing direct/cross risk dependencies
        13, 18, 20, 27,
        28, 29, 30,
        38, 39, 40,
        43, 44, 45, 46, 47, 48,

        # ISO 31000 outbound-sales risk
        31
    }
}

# =========================================================
# INCREMENTAL ANALYSIS HELPERS
# =========================================================

def normalise_question_id(value):
    text = (
        str(value or "")
        .replace("q", "")
        .replace("Q", "")
        .strip()
    )

    if not text.isdigit():
        return None

    question_id = int(text)

    if question_id < 1 or question_id > 48:
        return None

    return question_id


def affected_silos_for_questions(
    question_ids
) -> List[str]:
    """
    Return every user-facing silo whose evidence scope
    contains at least one changed assessment question.

    A question may affect several silos.
    """

    changed_ids = {
        question_id
        for question_id in (
            normalise_question_id(value)
            for value in (question_ids or [])
        )
        if question_id is not None
    }

    if not changed_ids:
        return []

    affected = []

    for silo_name, silo_question_ids in QUESTION_UPDATE_SILO_IDS.items():

        if changed_ids.intersection(
            silo_question_ids
        ):
            affected.append(
                silo_name
            )

    return affected


# =========================================================
# ANSWER HELPERS
# =========================================================

def get_answer(
    answers: Dict[str, Any],
    question_id: int
):
    return answers.get(
        str(question_id),
        answers.get(
            question_id
        )
    )


def build_answer_evidence(
    answers: Dict[str, Any],
    silo_name: str
) -> List[Dict[str, Any]]:
    """
    Convert raw numeric answer IDs into semantic evidence.

    Example:

        {
            "question_id": 38,
            "question": "Percentage of customers that are repeat customers",
            "answer": "25-50%"
        }

    Only questions relevant to the current silo are supplied.
    """

    allowed_ids = SILO_EVIDENCE_QUESTION_IDS.get(
        silo_name,
        set()
    )

    evidence = []

    for question_id in sorted(
        allowed_ids
    ):
        value = get_answer(
            answers,
            question_id
        )

        if value is None:
            continue

        if isinstance(
            value,
            str
        ) and not value.strip():
            continue

        if isinstance(
            value,
            list
        ) and not value:
            continue

        evidence.append({
            "question_id": question_id,
            "question": QUESTION_LABELS.get(
                question_id,
                f"Question {question_id}"
            ),
            "answer": value
        })

    return evidence

# =========================================================
# OFFICIAL ONTOLOGY RULE ENGINE
# =========================================================

def answer_text(
    answers: Dict[str, Any],
    question_id: int
) -> str:
    value = get_answer(
        answers,
        question_id
    )

    return str(
        value or ""
    ).strip()


def answer_lower(
    answers: Dict[str, Any],
    question_id: int
) -> str:
    return (
        answer_text(
            answers,
            question_id
        )
        .lower()
        .replace("–", "-")
        .replace("—", "-")
        .replace("_", "-")
        .replace("on-boarding", "onboarding")
        .strip()
    )

def make_rule_result(
    *,
    rule_id: str,
    silo: str,
    title: str,
    analysis: str,
    evidence_question_ids: List[int],
    recommendations: List[str],
    classification: str | None = None,
    kind: str = "rule",
    confidence: str = "high"
) -> Dict[str, Any]:

    return {
        "rule_id": rule_id,
        "silo": silo,
        "title": title,
        "analysis": analysis,
        "evidence_question_ids": evidence_question_ids,
        "recommendations": recommendations,
        "classification": classification,
        "kind": kind,
        "confidence": confidence
    }

def add_rule(
    results: Dict[str, List[Dict[str, Any]]],
    *,
    silo: str,
    rule_id: str,
    title: str,
    analysis: str,
    evidence_question_ids: List[int],
    recommendations: List[str] | None = None,
    classification: str | None = None,
    kind: str = "rule",
    confidence: str = "high"
):
    results[silo].append(
        make_rule_result(
            rule_id=rule_id,
            silo=silo,
            title=title,
            analysis=analysis,
            evidence_question_ids=list(
                dict.fromkeys(
                    evidence_question_ids
                )
            ),
            recommendations=(
                recommendations
                or []
            ),
            classification=classification,
            kind=kind,
            confidence=confidence
        )
    )

def answer_items(
    answers: Dict[str, Any],
    question_id: int
) -> List[str]:

    value = get_answer(
        answers,
        question_id
    )

    if isinstance(
        value,
        list
    ):
        raw_items = value

    else:
        raw_items = str(
            value or ""
        ).split(",")

    return [
        str(item).strip()
        for item in raw_items
        if str(
            item or ""
        ).strip()
    ]


def contains_any(
    text: str,
    values
) -> bool:

    text = str(
        text or ""
    ).lower()

    return any(
        str(value).lower()
        in text
        for value in values
    )


def numeric_score(
    answers: Dict[str, Any],
    question_id: int
):

    try:
        return float(
            answer_text(
                answers,
                question_id
            )
        )
    except Exception:
        return None


def percentage_midpoint(
    value: str
):

    text = (
        str(value or "")
        .lower()
        .replace("–", "-")
        .replace("—", "-")
        .replace("%", "")
        .strip()
    )

    mappings = {
        "0-20": 10.0,
        "5-15": 10.0,
        "10-25": 17.5,
        "15-25": 20.0,
        "20-40": 30.0,
        "25-50": 37.5,
        "40-60": 50.0,
        "50-75": 62.5,
        "60-80": 70.0,
        "75-100": 87.5,
        "80-100": 90.0
    }

    for key, midpoint in mappings.items():
        if key in text:
            return midpoint

    if (
        "<5" in text
        or "under 5" in text
    ):
        return 2.5

    if (
        "<10" in text
        or "under 10" in text
    ):
        return 5.0

    if (
        "<25" in text
        or "under 25" in text
    ):
        return 12.5

    if (
        ">75" in text
        or "over 75" in text
    ):
        return 87.5

    return None


def employee_count_upper_bound(
    answers: Dict[str, Any]
):

    value = answer_lower(
        answers,
        14
    )

    ranges = {
        "0-5": 5,
        "6-10": 10,
        "10-25": 25,
        "11-25": 25,
        "25-50": 50,
        "26-50": 50,
        "50+": 9999,
        "over 50": 9999
    }

    for key, upper in ranges.items():
        if key in value:
            return upper

    return None

def calculate_official_metrics(
    answers: Dict[str, Any]
) -> Dict[str, Any]:

    metrics = {}


    # =====================================================
    # NORMALISED SOURCE ANSWERS
    # =====================================================

    metrics["written_strategy"] = answer_lower(
        answers,
        11
    )

    metrics["goal_understanding"] = answer_lower(
        answers,
        10
    )

    metrics["admin_time"] = percentage_midpoint(
        answer_lower(
            answers,
            8
        )
    )

    metrics["duplication"] = answer_lower(
        answers,
        9
    )

    metrics["owner_independence"] = answer_lower(
        answers,
        13
    )

    metrics["growth_confidence"] = numeric_score(
        answers,
        7
    )

    metrics["turnover"] = percentage_midpoint(
        answer_lower(
            answers,
            18
        )
    )

    metrics["knowledge_concentration"] = (
        percentage_midpoint(
            answer_lower(
                answers,
                20
            )
        )
    )

    metrics["repeat_customer_midpoint"] = (
        percentage_midpoint(
            answer_lower(
                answers,
                38
            )
        )
    )

    metrics["inbound_midpoint"] = (
        percentage_midpoint(
            answer_lower(
                answers,
                31
            )
        )
    )

    metrics["recurring_midpoint"] = (
        percentage_midpoint(
            answer_lower(
                answers,
                30
            )
        )
    )

    metrics["revenue_concentration_midpoint"] = (
        percentage_midpoint(
            answer_lower(
                answers,
                28
            )
        )
    )

    metrics["quality_score"] = numeric_score(
        answers,
        39
    )

    metrics["referral_score"] = numeric_score(
        answers,
        40
    )


    # =====================================================
    # OPERATIONS — RULE 3.1 DIGITAL INTENSITY
    # =====================================================

    software = answer_lower(
        answers,
        22
    )

    automation = answer_lower(
        answers,
        23
    )

    ai_experimentation = answer_lower(
        answers,
        24
    )

    readiness = numeric_score(
        answers,
        26
    )

    software_score = None

    if software == "yes":
        software_score = 100

    elif "some" in software:
        software_score = 60

    elif "not enough" in software:
        software_score = 40

    elif software in {
        "none",
        "no"
    }:
        software_score = 0


    automation_score = (
        100
        if automation == "yes"
        else 0
        if automation == "no"
        else None
    )

    ai_score = (
        100
        if ai_experimentation == "yes"
        else 0
        if ai_experimentation == "no"
        else None
    )

    readiness_score = (
        readiness * 10
        if readiness is not None
        else None
    )

    digital_components = [
        software_score,
        automation_score,
        ai_score,
        readiness_score
    ]

    if all(
        component is not None
        for component in digital_components
    ):
        metrics["digital_intensity"] = (
            sum(
                digital_components
            )
            / len(
                digital_components
            )
        )

    else:
        metrics["digital_intensity"] = None


    # =====================================================
    # OPERATIONS — RULE 3.2 TRANSFORMATION MANAGEMENT
    # =====================================================

    sop = answer_lower(
        answers,
        21
    )

    if (
        "all" in sop
        and "some" not in sop
    ):
        sop_score = 100

    elif "most" in sop:
        sop_score = 75

    elif "some" in sop:
        sop_score = 40

    elif sop == "no":
        sop_score = 0

    else:
        sop_score = None


    strategy_score = (
        100
        if metrics[
            "written_strategy"
        ] == "yes"
        else 0
        if metrics[
            "written_strategy"
        ] == "no"
        else None
    )

    if metrics[
        "goal_understanding"
    ] == "yes":
        goal_score = 100

    elif metrics[
        "goal_understanding"
    ] == "some":
        goal_score = 60

    elif metrics[
        "goal_understanding"
    ] == "no":
        goal_score = 0

    else:
        goal_score = None


    transformation_parts = [
        sop_score,
        strategy_score,
        goal_score
    ]

    if all(
        part is not None
        for part in transformation_parts
    ):
        metrics[
            "transformation_management"
        ] = (
            sum(
                transformation_parts
            )
            / 3
        )

    else:
        metrics[
            "transformation_management"
        ] = None


    # =====================================================
    # RULE 3.3 MIT DIGITAL MATURITY
    # =====================================================

    digital = metrics.get(
        "digital_intensity"
    )

    transformation = metrics.get(
        "transformation_management"
    )

    quadrant = None

    if (
        digital is not None
        and transformation is not None
    ):

        if (
            digital >= 60
            and transformation >= 60
        ):
            quadrant = "DIGIRATI"

        elif (
            digital >= 60
            and transformation < 60
        ):
            quadrant = "FASHIONISTA"

        elif (
            digital < 60
            and transformation >= 60
        ):
            quadrant = "CONSERVATIVE"

        else:
            quadrant = "BEGINNER"

    metrics[
        "digital_maturity_quadrant"
    ] = quadrant


    # =====================================================
    # FINANCE — RULE 4.1 DIVERSIFICATION SCORE
    # =====================================================

    concentration = metrics.get(
        "revenue_concentration_midpoint"
    )

    diversification_score = None
    concentration_classification = None

    if concentration is not None:

        if concentration >= 75:
            diversification_score = 10
            concentration_classification = "CRITICAL"

        elif concentration >= 50:
            diversification_score = 30
            concentration_classification = "HIGH"

        elif concentration >= 25:
            diversification_score = 50
            concentration_classification = "MODERATE"

        elif concentration >= 15:
            diversification_score = 80
            concentration_classification = "LOW"

        else:
            diversification_score = 100
            concentration_classification = "LOW"

    metrics[
        "diversification_score"
    ] = diversification_score

    metrics[
        "revenue_concentration_classification"
    ] = concentration_classification


    # =====================================================
    # FINANCE — RULE 4.3 BUSINESS MODEL
    # =====================================================

    recurring = metrics.get(
        "recurring_midpoint"
    )

    if recurring is None:
        business_model = None
        predictability = None

    elif recurring >= 75:
        business_model = "SUBSCRIPTION"
        predictability = "HIGH"

    elif recurring >= 25:
        business_model = "HYBRID"
        predictability = "MEDIUM"

    else:
        business_model = "PROJECT-BASED"
        predictability = "LOW"

    metrics[
        "business_model"
    ] = business_model

    metrics[
        "revenue_predictability"
    ] = predictability


    # =====================================================
    # FINANCE — RULE 4.4 CCC
    # =====================================================

    dso = None

    if business_model == "SUBSCRIPTION":
        dso = 15

    elif business_model == "HYBRID":
        dso = 45

    elif business_model == "PROJECT-BASED":
        dso = 60

    if (
        dso is not None
        and answer_lower(
            answers,
            29
        ) == "yes"
    ):
        dso *= 1.20

    if dso is not None:

        dio = 0
        dpo = 30

        metrics["ccc_days"] = (
            dio
            + dso
            - dpo
        )

    else:
        metrics["ccc_days"] = None


    ccc = metrics.get(
        "ccc_days"
    )

    if ccc is None:
        cash_efficiency = None
        cash_efficiency_score = None

    elif ccc <= 20:
        cash_efficiency = "EXCELLENT"
        cash_efficiency_score = 100

    elif ccc <= 40:
        cash_efficiency = "GOOD"
        cash_efficiency_score = 75

    elif ccc <= 60:
        cash_efficiency = "POOR"
        cash_efficiency_score = 50

    else:
        cash_efficiency = "CRITICAL"
        cash_efficiency_score = 25

    metrics[
        "cash_efficiency"
    ] = cash_efficiency

    metrics[
        "cash_efficiency_score"
    ] = cash_efficiency_score


    # =====================================================
    # FINANCE — RULE 4.6 NET PROFIT MARGIN ESTIMATE
    # =====================================================

    estimated_npm = 15.0

    if answer_lower(
        answers,
        29
    ) == "yes":
        estimated_npm *= 0.85

    if (
        metrics.get(
            "admin_time"
        )
        is not None
        and metrics[
            "admin_time"
        ] > 50
    ):
        estimated_npm *= 0.90

    if (
        sop_score is not None
        and sop_score <= 40
    ):
        estimated_npm *= 0.92

    metrics[
        "estimated_net_profit_margin"
    ] = estimated_npm


    # =====================================================
    # FINANCE — RULE 4.7 ASSET TURNOVER
    # =====================================================

    estimated_asset_turnover = 2.0

    employee_upper = employee_count_upper_bound(
        answers
    )

    if (
        employee_upper is not None
        and employee_upper > 50
    ):
        estimated_asset_turnover *= 0.9

    if (
        digital is not None
        and digital >= 70
    ):
        estimated_asset_turnover *= 1.1

    metrics[
        "estimated_asset_turnover"
    ] = estimated_asset_turnover


    # =====================================================
    # FINANCE — RULE 4.8 ROE
    # =====================================================

    estimated_leverage = 1.5

    metrics[
        "estimated_financial_leverage"
    ] = estimated_leverage

    metrics[
        "estimated_roe"
    ] = (
        estimated_npm
        / 100
        * estimated_asset_turnover
        * estimated_leverage
        * 100
    )


    # =====================================================
    # MARKETING — 5.1 SEGMENTATION
    # =====================================================

    target_segments = answer_items(
        answers,
        33
    )

    segment_count = len(
        target_segments
    )

    if 1 <= segment_count <= 3:
        segmentation_score = 90
        segmentation_classification = "FOCUSED"

    elif 4 <= segment_count <= 6:
        segmentation_score = 70
        segmentation_classification = "MODERATE"

    elif segment_count >= 7:
        segmentation_score = 40
        segmentation_classification = "FRAGMENTED"

    else:
        segmentation_score = None
        segmentation_classification = None

    metrics[
        "segmentation_score"
    ] = segmentation_score

    metrics[
        "segmentation_classification"
    ] = segmentation_classification


    # =====================================================
    # SERVICE — RETENTION SCORE
    # =====================================================

    repeat_mid = metrics.get(
        "repeat_customer_midpoint"
    )

    if repeat_mid is None:
        retention_score = None

    else:
        retention_score = repeat_mid

    metrics[
        "retention_score"
    ] = retention_score


    # =====================================================
    # SERVICE — RULE 6.10 ESTIMATED NPS
    # =====================================================

    quality = metrics.get(
        "quality_score"
    )

    referral = metrics.get(
        "referral_score"
    )

    if (
        quality is not None
        and referral is not None
    ):
        promoter = (
            referral
            / 5
            * 100
        )

        detractor = (
            (
                5
                - quality
            )
            / 5
            * 30
        )

        metrics[
            "estimated_nps"
        ] = (
            promoter
            - detractor
        )

    else:
        metrics[
            "estimated_nps"
        ] = None


    return metrics
    
def evaluate_official_ontology_rules(
    answers: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Deterministically apply official PULSE ontology rules.

    IMPORTANT:
    Current GLOBAL question IDs are used here.
    The old/local question numbers in the rules document
    are mapped semantically to the current 1-48 assessment.
    """

    results = {
        silo_name: []
        for silo_name in SILO_EVIDENCE_QUESTION_IDS.keys()
    }

    metrics = calculate_official_metrics(
        answers
    )


    # =====================================================
    # STRATEGY — RULE 1.1 STRATEGIC CLARITY
    # Current Q10 = employee goal understanding
    # Current Q11 = written strategy
    # =====================================================

    goal_understanding = answer_lower(
        answers,
        10
    )

    written_strategy = answer_lower(
        answers,
        11
    )

    if (
        written_strategy == "yes"
        and goal_understanding in {
            "yes",
            "some"
        }
    ):
        results["strategy"].append(
            make_rule_result(
                rule_id="1.1",
                silo="strategy",
                title="Strategic clarity is high",
                analysis=(
                    "A written strategy or growth plan exists and "
                    "employees report at least some understanding of "
                    "the company's goals and direction."
                ),
                evidence_question_ids=[
                    10,
                    11
                ],
                recommendations=[
                    "Continue cascading the written strategy into clear team and departmental objectives."
                ],
                classification="HIGH"
            )
        )

    elif (
        written_strategy == "no"
        and goal_understanding == "no"
    ):
        results["strategy"].append(
            make_rule_result(
                rule_id="1.1",
                silo="strategy",
                title="Strategic clarity is critically low",
                analysis=(
                    "There is no written strategy and employees do "
                    "not understand the company's direction."
                ),
                evidence_question_ids=[
                    10,
                    11
                ],
                recommendations=[
                    "Create a written strategy and establish a structured strategy communication process."
                ],
                classification="CRITICALLY LOW"
            )
        )

    elif written_strategy or goal_understanding:
        results["strategy"].append(
            make_rule_result(
                rule_id="1.1",
                silo="strategy",
                title="Strategic clarity is medium",
                analysis=(
                    "Strategy documentation and employee understanding "
                    "are only partially aligned."
                ),
                evidence_question_ids=[
                    10,
                    11
                ],
                recommendations=[
                    "Strengthen the connection between the written strategy and employee understanding."
                ],
                classification="MEDIUM"
            )
        )


    # =====================================================
    # HR — TURNOVER SEVERITY
    # Official HR Q5 -> Current Q18
    # =====================================================

    turnover = answer_lower(
        answers,
        18
    )

    turnover_classification = None

    if "under 25" in turnover or "<25" in turnover:
        turnover_classification = "HEALTHY"

    elif "25-50" in turnover:
        turnover_classification = "CONCERNING"

    elif "50-75" in turnover:
        turnover_classification = "CRITICAL"

    elif (
        "75-100" in turnover
        or ">75" in turnover
        or "over 75" in turnover
    ):
        turnover_classification = "CRISIS"

    if turnover_classification:
        results["people"].append(
            make_rule_result(
                rule_id="HR-TURNOVER-SEVERITY",
                silo="people",
                title=(
                    f"Employee turnover is classified as "
                    f"{turnover_classification.lower()}"
                ),
                analysis=(
                    f"The reported employee turnover range is "
                    f"{answer_text(answers, 18)}. Under the official "
                    f"PULSE turnover thresholds this is classified "
                    f"as {turnover_classification}."
                ),
                evidence_question_ids=[
                    18
                ],
                recommendations=[
                    "Investigate the causes of turnover and implement targeted retention measures."
                ],
                classification=turnover_classification
            )
        )


    # =====================================================
    # HR — RULE 2.7 TURNOVER CRISIS
    # >=50% turnover triggers crisis
    # =====================================================

    turnover_at_least_50 = (
        "50-75" in turnover
        or "75-100" in turnover
        or ">75" in turnover
        or "over 75" in turnover
    )

    if turnover_at_least_50:
        results["people"].append(
            make_rule_result(
                rule_id="2.7",
                silo="people",
                title="Turnover crisis detected",
                analysis=(
                    "Employee turnover is at least 50%, which triggers "
                    "the official PULSE turnover crisis rule."
                ),
                evidence_question_ids=[
                    18
                ],
                recommendations=[
                    "Prioritise retention before attempting major organisational scaling."
                ],
                classification="CRISIS"
            )
        )


    # =====================================================
    # HR — KNOWLEDGE CONCENTRATION
    # Official HR Q7 -> Current Q20
    # =====================================================

    concentration = answer_lower(
        answers,
        20
    )

    concentration_classification = None

    if (
        "<10" in concentration
        or "under 10" in concentration
    ):
        concentration_classification = "LOW"

    elif "10-25" in concentration:
        concentration_classification = "MEDIUM"

    elif "25-50" in concentration:
        concentration_classification = "HIGH"

    elif (
        ">50" in concentration
        or "50-75" in concentration
        or "75-100" in concentration
        or "over 50" in concentration
    ):
        concentration_classification = "CRITICAL"

    if concentration_classification:
        results["people"].append(
            make_rule_result(
                rule_id="HR-KNOWLEDGE-CONCENTRATION",
                silo="people",
                title=(
                    "Knowledge concentration risk is "
                    f"{concentration_classification.lower()}"
                ),
                analysis=(
                    f"{answer_text(answers, 20)} of critical client "
                    f"relationships or technical expertise is "
                    f"concentrated in one individual."
                ),
                evidence_question_ids=[
                    20
                ],
                recommendations=[
                    "Document critical knowledge and expand cross-training and succession coverage."
                ],
                classification=concentration_classification
            )
        )


    # =====================================================
    # HR/RISK — RULE 2.8 + CROSS-RULE CS.5
    # concentration >=25 AND turnover >=25
    # =====================================================

    concentration_at_least_25 = (
        "25-50" in concentration
        or "50-75" in concentration
        or "75-100" in concentration
        or ">50" in concentration
        or "over 50" in concentration
    )

    turnover_at_least_25 = (
        "25-50" in turnover
        or turnover_at_least_50
    )

    if (
        concentration_at_least_25
        and turnover_at_least_25
    ):
        results["people"].append(
            make_rule_result(
                rule_id="2.8",
                silo="people",
                title="Succession risk is critical",
                analysis=(
                    "Knowledge concentration is at least 25% and "
                    "employee turnover is at least 25%, triggering "
                    "the official succession-risk rule."
                ),
                evidence_question_ids=[
                    18,
                    20
                ],
                recommendations=[
                    "Document critical knowledge.",
                    "Cross-train backup personnel.",
                    "Create a retention plan for key individuals."
                ],
                classification="CRITICAL"
            )
        )

        results["risk"].append(
            make_rule_result(
                rule_id="CS.5",
                silo="risk",
                title="Knowledge loss from turnover is a high risk",
                analysis=(
                    "The combination of elevated employee turnover "
                    "and concentrated knowledge triggers the official "
                    "HR-Knowledge Concentration-Risk Cascade."
                ),
                evidence_question_ids=[
                    18,
                    20
                ],
                recommendations=[
                    "Run a 90-day knowledge capture sprint covering tutorials, documented decisions and shadowing."
                ],
                classification="HIGH"
            )
        )


    # =====================================================
    # OPERATIONS — RULE 3.6 VENDOR RISK
    # =====================================================

    vendor_backup = answer_lower(
        answers,
        27
    )

    operational_bottleneck = answer_lower(
        answers,
        4
    )

    vendor_bottleneck = (
        "supplier/vendor dependencies" in operational_bottleneck
        or "vendor dependencies" in operational_bottleneck
        or "supplier dependencies" in operational_bottleneck
    )

    if (
        vendor_backup == "no"
        and vendor_bottleneck
    ):
        add_rule(
            results,
            silo="operations",
            rule_id="3.6",
            title="Vendor concentration risk is high",
            analysis=(
                "No pre-vetted Tier-2 alternatives are available "
                "and the primary operational bottleneck is vendor "
                "dependency. Official Rule 3.6 therefore classifies "
                "vendor concentration risk as HIGH."
            ),
            evidence_question_ids=[
                4,
                27
            ],
            recommendations=[
                "Develop Tier-2 vendor relationships immediately."
            ],
            classification="HIGH"
        )

    elif "for some" in vendor_backup:
        add_rule(
            results,
            silo="operations",
            rule_id="3.6",
            title="Vendor concentration risk is medium",
            analysis=(
                "Pre-vetted Tier-2 alternatives exist for only "
                "some critical suppliers or services."
            ),
            evidence_question_ids=[
                27
            ],
            recommendations=[
                "Audit which critical vendors lack alternatives."
            ],
            classification="MEDIUM"
        )

    elif (
        "for all critical services" in vendor_backup
        or "all critical services" in vendor_backup
    ):
        add_rule(
            results,
            silo="operations",
            rule_id="3.6",
            title="Vendor concentration risk is low",
            analysis=(
                "Pre-vetted alternatives are available for all "
                "critical services, which places vendor dependency "
                "in the LOW-risk category."
            ),
            evidence_question_ids=[
                27
            ],
            recommendations=[],
            classification="LOW"
        )


    # =====================================================
    # OPERATIONS — RULE 3.8 DIGITAL READINESS REALITY CHECK
    #
    # Current mappings:
    # Q21 = SOP coverage
    # Q22 = software/systems
    # Q23 = automation
    # Q26 = self-assessed digital readiness
    # =====================================================

    digital_readiness_text = answer_text(
        answers,
        26
    )

    try:
        digital_readiness_score = float(
            digital_readiness_text
        )
    except Exception:
        digital_readiness_score = None


    software_tools = answer_lower(
        answers,
        22
    )

    automation = answer_lower(
        answers,
        23
    )

    sop_coverage = answer_lower(
        answers,
        21
    )


    digital_infrastructure_gap = (
        software_tools in {
            "none",
            "not enough"
        }
        or automation == "no"
        or sop_coverage == "no"
    )


    if (
        digital_readiness_score is not None
        and digital_readiness_score >= 7
        and digital_infrastructure_gap
    ):

        adjusted_readiness_score = (
            digital_readiness_score
            * 0.60
        )

        results["operations"].append(
            make_rule_result(
                rule_id="3.8",
                silo="operations",
                title="Digital readiness perception gap detected",
                analysis=(
                    f"Self-assessed digital readiness is "
                    f"{digital_readiness_score:g}, but the supporting "
                    f"digital or process infrastructure does not meet "
                    f"the official rule requirements. Rule 3.8 applies "
                    f"the prescribed 40% downward adjustment, producing "
                    f"a rule-derived readiness value of "
                    f"{adjusted_readiness_score:g}."
                ),
                evidence_question_ids=[
                    21,
                    22,
                    23,
                    26
                ],
                recommendations=[
                    "Strengthen the missing digital and process foundations before treating the self-assessed readiness score as achieved maturity."
                ],
                classification="PERCEPTION GAP",
                kind="estimated_rule",
                confidence="high"
            )
        )

    sop_incomplete = (
        sop_coverage == "no"
        or sop_coverage == "some"
        or sop_coverage == "yes for some"
    )


    if sop_incomplete:

        # -------------------------------------------------
        # STRATEGY EFFECT
        # -------------------------------------------------

        results["strategy"].append(
            make_rule_result(
                rule_id="3.9",
                silo="strategy",
                title="Incomplete SOP coverage constrains systems effectiveness",
                analysis=(
                    "Important processes are not fully documented. "
                    "Under official Rule 3.9, incomplete SOP coverage "
                    "reduces the Systems component of the strategy "
                    "framework."
                ),
                evidence_question_ids=[
                    21
                ],
                recommendations=[
                    "Expand SOP documentation across critical processes."
                ],
                classification=None,
                kind="rule",
                confidence="high"
            )
        )


        # -------------------------------------------------
        # SERVICE EFFECT
        # -------------------------------------------------

        results["service"].append(
            make_rule_result(
                rule_id="3.9",
                silo="service",
                title="Incomplete SOP coverage creates service consistency risk",
                analysis=(
                    "Important processes are documented only partially "
                    "or not at all. Official Rule 3.9 therefore creates "
                    "a service-consistency risk."
                ),
                evidence_question_ids=[
                    21
                ],
                recommendations=[
                    "Standardise service-critical processes through complete SOP coverage."
                ],
                classification="RISK",
                kind="rule",
                confidence="high"
            )
        )


        # -------------------------------------------------
        # PEOPLE EFFECT
        # -------------------------------------------------

        results["people"].append(
            make_rule_result(
                rule_id="3.9",
                silo="people",
                title="Incomplete SOP coverage limits accountability",
                analysis=(
                    "Incomplete process documentation constrains "
                    "accountability under official Rule 3.9."
                ),
                evidence_question_ids=[
                    21
                ],
                recommendations=[
                    "Link documented processes to clear role ownership and accountability."
                ],
                classification=None,
                kind="rule",
                confidence="high"
            )
        )

    # =====================================================
    # OPERATIONS — RULE 3.1 DIGITAL INTENSITY
    # =====================================================

    digital_intensity = metrics.get(
        "digital_intensity"
    )

    if digital_intensity is not None:

        if digital_intensity >= 60:
            digital_intensity_classification = "HIGH"
        elif digital_intensity < 40:
            digital_intensity_classification = "LOW"
        else:
            digital_intensity_classification = "MODERATE"

        add_rule(
            results,
            silo="operations",
            rule_id="3.1",
            title=(
                "Digital intensity is "
                f"{digital_intensity_classification.lower()}"
            ),
            analysis=(
                f"Official Rule 3.1 combines software usage, "
                f"automation, AI experimentation and digital "
                f"readiness. The calculated digital intensity is "
                f"{digital_intensity:.1f}%."
            ),
            evidence_question_ids=[
                22,
                23,
                24,
                26
            ],
            recommendations=[],
            classification=digital_intensity_classification,
            kind="estimated_rule",
            confidence="high"
        )


    # =====================================================
    # OPERATIONS — RULE 3.2 TRANSFORMATION MANAGEMENT
    # =====================================================

    transformation_management = metrics.get(
        "transformation_management"
    )

    if transformation_management is not None:

        if transformation_management >= 60:
            transformation_classification = "STRONG"
        elif transformation_management < 40:
            transformation_classification = "WEAK"
        else:
            transformation_classification = "MODERATE"

        add_rule(
            results,
            silo="operations",
            rule_id="3.2",
            title=(
                "Transformation management is "
                f"{transformation_classification.lower()}"
            ),
            analysis=(
                f"Official Rule 3.2 combines SOP coverage, written "
                f"strategy and employee understanding. The calculated "
                f"transformation-management score is "
                f"{transformation_management:.1f}%."
            ),
            evidence_question_ids=[
                10,
                11,
                21
            ],
            recommendations=[],
            classification=transformation_classification,
            kind="estimated_rule",
            confidence="high"
        )


    # =====================================================
    # OPERATIONS — RULE 3.3 MIT DIGITAL MATURITY QUADRANT
    # =====================================================

    digital_quadrant = metrics.get(
        "digital_maturity_quadrant"
    )

    if digital_quadrant:

        quadrant_analysis = {
            "DIGIRATI": (
                "Digital intensity and transformation management "
                "are both at least 60%."
            ),
            "FASHIONISTA": (
                "Digital intensity is at least 60% while "
                "transformation management remains below 60%."
            ),
            "CONSERVATIVE": (
                "Transformation management is at least 60% while "
                "digital intensity remains below 60%."
            ),
            "BEGINNER": (
                "Both digital intensity and transformation management "
                "are below 60%."
            )
        }

        quadrant_recommendations = {
            "DIGIRATI": [],
            "FASHIONISTA": [
                "Strengthen process documentation before buying more technology."
            ],
            "CONSERVATIVE": [
                "Pilot automation projects in high-ROI areas."
            ],
            "BEGINNER": [
                "Focus on process standardisation before technology investment."
            ]
        }

        add_rule(
            results,
            silo="operations",
            rule_id="3.3",
            title=(
                "MIT digital maturity quadrant is "
                f"{digital_quadrant.lower()}"
            ),
            analysis=quadrant_analysis[
                digital_quadrant
            ],
            evidence_question_ids=[
                10,
                11,
                21,
                22,
                23,
                24,
                26
            ],
            recommendations=quadrant_recommendations[
                digital_quadrant
            ],
            classification=digital_quadrant,
            kind="estimated_rule",
            confidence="high"
        )

    # =====================================================
    # OPERATIONS — RULE 3.10 TRANSFORMATION ROADMAP
    # =====================================================

    if digital_quadrant:

        roadmap = {
            "BEGINNER": [
                "Document core processes.",
                "Eliminate the primary operational bottleneck.",
                "Pilot automation in the highest-priority AI area."
            ],
            "FASHIONISTA": [
                "Audit technology ROI and actual tool usage.",
                "Standardise processes.",
                "Align technology spending to strategy."
            ],
            "CONSERVATIVE": [
                "Identify high-impact automation opportunities.",
                "Pilot AI in the top-priority area.",
                "Scale successful pilots."
            ],
            "DIGIRATI": [
                "Optimise existing systems.",
                "Move into advanced AI integration.",
                "Build competitive advantage through technology."
            ]
        }

        add_rule(
            results,
            silo="operations",
            rule_id="3.10",
            title="Transformation roadmap generated",
            analysis=(
                f"Official Rule 3.10 applies the "
                f"{digital_quadrant} transformation roadmap."
            ),
            evidence_question_ids=[
                4,
                21,
                25
            ],
            recommendations=roadmap[
                digital_quadrant
            ],
            classification=digital_quadrant,
            kind="rule",
            confidence="high"
        )


    # =====================================================
    # FINANCIAL — RULE 4.1 REVENUE CONCENTRATION
    # =====================================================

    concentration_classification = (
        metrics.get(
            "revenue_concentration_classification"
        )
    )

    diversification_score = (
        metrics.get(
            "diversification_score"
        )
    )

    if concentration_classification:

        add_rule(
            results,
            silo="financial",
            rule_id="4.1",
            title=(
                "Customer revenue concentration risk is "
                f"{concentration_classification.lower()}"
            ),
            analysis=(
                f"The largest-customer revenue range is "
                f"{answer_text(answers, 28)}. "
                f"Official Rule 4.1 classifies the "
                f"concentration risk as "
                f"{concentration_classification}, with a "
                f"diversification score of "
                f"{diversification_score}%."
            ),
            evidence_question_ids=[
                28
            ],
            recommendations=(
                [
                    "Prioritise customer diversification immediately."
                ]
                if concentration_classification in {
                    "HIGH",
                    "CRITICAL"
                }
                else
                [
                    "Maintain an appropriately diversified customer base."
                ]
            ),
            classification=concentration_classification
        )

    # =====================================================
    # FINANCIAL — RULE 4.2 CONCENTRATION CROSS-SILO ALERTS
    # =====================================================

    if concentration_classification in {
        "HIGH",
        "CRITICAL"
    }:

        add_rule(
            results,
            silo="strategy",
            rule_id="4.2",
            title="Strategy must prioritise customer diversification",
            analysis=(
                "Customer concentration is HIGH or CRITICAL. "
                "Official Rule 4.2 requires customer diversification "
                "to become a strategic priority."
            ),
            evidence_question_ids=[
                28
            ],
            recommendations=[
                "Prioritise customer diversification before taking additional concentration risk."
            ],
            classification=concentration_classification
        )

        add_rule(
            results,
            silo="marketing",
            rule_id="4.2",
            title="Sales must expand the customer base",
            analysis=(
                "Customer concentration is HIGH or CRITICAL. "
                "Official Rule 4.2 requires Sales and Marketing "
                "to expand the customer base."
            ),
            evidence_question_ids=[
                28
            ],
            recommendations=[
                "Increase acquisition activity aimed at reducing dependence on the largest customer."
            ],
            classification=concentration_classification
        )

        add_rule(
            results,
            silo="risk",
            rule_id="4.2",
            title="High customer dependency risk detected",
            analysis=(
                "HIGH or CRITICAL customer concentration triggers "
                "the official customer-dependency risk alert."
            ),
            evidence_question_ids=[
                28
            ],
            recommendations=[
                "Track customer concentration as a material enterprise risk."
            ],
            classification=concentration_classification
        )


    # =====================================================
    # FINANCIAL — RULE 4.3 BUSINESS MODEL
    # =====================================================

    business_model = metrics.get(
        "business_model"
    )

    predictability = metrics.get(
        "revenue_predictability"
    )

    if business_model:

        add_rule(
            results,
            silo="financial",
            rule_id="4.3",
            title=(
                f"Business model is "
                f"{business_model.lower()} with "
                f"{predictability.lower()} revenue predictability"
            ),
            analysis=(
                f"Recurring revenue is reported as "
                f"{answer_text(answers, 30)}. "
                f"Official Rule 4.3 classifies this as a "
                f"{business_model} model with "
                f"{predictability} revenue predictability."
            ),
            evidence_question_ids=[
                30
            ],
            recommendations=(
                [
                    "Develop recurring revenue streams to improve cash-flow predictability."
                ]
                if business_model == "PROJECT-BASED"
                else []
            ),
            classification=predictability
        )

    # =====================================================
    # FINANCE — RULE 4.4 CCC
    # =====================================================

    ccc_days = metrics.get(
        "ccc_days"
    )

    if ccc_days is not None:

        add_rule(
            results,
            silo="financial",
            rule_id="4.4",
            title="Estimated cash conversion cycle calculated",
            analysis=(
                f"The official service-business CCC model produces "
                f"an estimated cash conversion cycle of "
                f"{ccc_days:.1f} days."
            ),
            evidence_question_ids=[
                29,
                30
            ],
            recommendations=[
                "Use the estimated CCC as a working-capital diagnostic, not as a measured accounting value."
            ],
            classification=None,
            kind="estimated_rule",
            confidence="medium"
        )


    # =====================================================
    # FINANCE — RULE 4.5 CASH EFFICIENCY
    # =====================================================

    cash_efficiency = metrics.get(
        "cash_efficiency"
    )

    if cash_efficiency:

        add_rule(
            results,
            silo="financial",
            rule_id="4.5",
            title=(
                "Working-capital efficiency is "
                f"{cash_efficiency.lower()}"
            ),
            analysis=(
                f"The estimated CCC is "
                f"{ccc_days:.1f} days, which Rule 4.5 "
                f"classifies as {cash_efficiency}."
            ),
            evidence_question_ids=[
                29,
                30
            ],
            recommendations=(
                [
                    "Improve collection processes and working-capital controls."
                ]
                if cash_efficiency in {
                    "POOR",
                    "CRITICAL"
                }
                else []
            ),
            classification=cash_efficiency,
            kind="estimated_rule",
            confidence="medium"
        )


    # =====================================================
    # FINANCE — RULE 4.6 DUPONT NPM ESTIMATE
    # =====================================================

    estimated_npm = metrics[
        "estimated_net_profit_margin"
    ]

    add_rule(
        results,
        silo="financial",
        rule_id="4.6",
        title="Estimated net profit margin",
        analysis=(
            f"Using the official DuPont service-business baseline "
            f"and its prescribed inefficiency multipliers, "
            f"estimated net profit margin is "
            f"{estimated_npm:.1f}%. This is an ontology estimate, "
            f"not reported financial performance."
        ),
        evidence_question_ids=[
            8,
            21,
            29
        ],
        recommendations=[
            "Validate this estimated margin against actual management accounts."
        ],
        classification=None,
        kind="estimated_rule",
        confidence="medium"
    )


    # =====================================================
    # FINANCE — RULE 4.7 ASSET TURNOVER ESTIMATE
    # =====================================================

    add_rule(
        results,
        silo="financial",
        rule_id="4.7",
        title="Estimated asset turnover",
        analysis=(
            f"Official Rule 4.7 produces an estimated asset "
            f"turnover of "
            f"{metrics['estimated_asset_turnover']:.2f}."
        ),
        evidence_question_ids=[
            14,
            22,
            23,
            24,
            26
        ],
        recommendations=[
            "Validate the estimated asset-utilisation ratio against actual balance-sheet and revenue data."
        ],
        kind="estimated_rule",
        confidence="medium"
    )


    # =====================================================
    # FINANCE — RULE 4.8 ESTIMATED ROE
    # =====================================================

    add_rule(
        results,
        silo="financial",
        rule_id="4.8",
        title="Estimated DuPont return on equity",
        analysis=(
            f"The official DuPont estimate combines the "
            f"estimated margin, asset turnover and the document's "
            f"1.5 leverage assumption. Estimated ROE is "
            f"{metrics['estimated_roe']:.1f}%."
        ),
        evidence_question_ids=[
            8,
            14,
            21,
            22,
            23,
            24,
            26,
            29
        ],
        recommendations=[
            "Treat this as a framework estimate until actual financial statements are connected."
        ],
        kind="estimated_rule",
        confidence="medium"
    )


    

    # =====================================================
    # MARKETING — RULE 5.1 SEGMENTATION
    # Current Q33
    # =====================================================

    target_segments = [
        item.strip()
        for item in answer_text(
            answers,
            33
        ).split(",")
        if item.strip()
    ]

    segment_count = len(
        target_segments
    )

    if 1 <= segment_count <= 3:
        results["marketing"].append(
            make_rule_result(
                rule_id="5.1",
                silo="marketing",
                title="Market segmentation is focused",
                analysis=(
                    f"The business selected {segment_count} primary "
                    "target customer segments. Under the official "
                    "STP rule this is classified as FOCUSED."
                ),
                evidence_question_ids=[
                    33
                ],
                recommendations=[
                    "Keep marketing messages tailored to the selected priority customer segments."
                ],
                classification="FOCUSED"
            )
        )

    elif 4 <= segment_count <= 6:
        results["marketing"].append(
            make_rule_result(
                rule_id="5.1",
                silo="marketing",
                title="Market segmentation is moderate",
                analysis=(
                    f"The business selected {segment_count} target "
                    "segments, which the official rule classifies "
                    "as MODERATE."
                ),
                evidence_question_ids=[
                    33
                ],
                recommendations=[
                    "Review whether marketing resources are spread too widely."
                ],
                classification="MODERATE"
            )
        )

    elif segment_count >= 7:
        results["marketing"].append(
            make_rule_result(
                rule_id="5.1",
                silo="marketing",
                title="Market segmentation is fragmented",
                analysis=(
                    f"The business selected {segment_count} target "
                    "segments, which the official rule classifies "
                    "as FRAGMENTED."
                ),
                evidence_question_ids=[
                    33
                ],
                recommendations=[
                    "Narrow target segments to improve marketing efficiency."
                ],
                classification="FRAGMENTED"
            )
        )


    # =====================================================
    # MARKETING — LEAD SOURCE BALANCE
    # Current Q31
    # =====================================================

    inbound = answer_lower(
        answers,
        31
    )

    if (
        "0-20" in inbound
        or "20-40" in inbound
    ):
        results["marketing"].append(
            make_rule_result(
                rule_id="5-LEAD-SOURCE-BALANCE",
                silo="marketing",
                title="Lead generation is outbound dependent",
                analysis=(
                    "The inbound lead percentage falls below the "
                    "40% midpoint threshold used by the official "
                    "PULSE lead-source rule."
                ),
                evidence_question_ids=[
                    31
                ],
                recommendations=[
                    "Strengthen inbound marketing while maintaining effective outbound acquisition."
                ],
                classification="OUTBOUND DEPENDENT"
            )
        )


    # =====================================================
    # SERVICE — RETENTION HEALTH
    # Current Q38
    # =====================================================

    repeat_customers = answer_lower(
        answers,
        38
    )

    retention_classification = None

    if "25-50" in repeat_customers:
        retention_classification = "FAIR"

    elif "50-75" in repeat_customers:
        retention_classification = "GOOD"

    elif (
        ">75" in repeat_customers
        or "75-100" in repeat_customers
        or "over 75" in repeat_customers
    ):
        retention_classification = "EXCELLENT"

    elif (
        "<25" in repeat_customers
        or "under 25" in repeat_customers
    ):
        retention_classification = "POOR"

    if retention_classification:
        results["service"].append(
            make_rule_result(
                rule_id="6-RETENTION-HEALTH",
                silo="service",
                title=(
                    "Customer retention is "
                    f"{retention_classification.lower()}"
                ),
                analysis=(
                    f"The reported repeat-customer range is "
                    f"{answer_text(answers, 38)}, which the official "
                    f"PULSE retention thresholds classify as "
                    f"{retention_classification}."
                ),
                evidence_question_ids=[
                    38
                ],
                recommendations=[
                    "Investigate the drivers of repeat business and customer churn."
                ],
                classification=retention_classification
            )
        )

    # =====================================================
    # SERVICE — RULE 6.10 ESTIMATED NPS
    # =====================================================

    estimated_nps = metrics.get(
        "estimated_nps"
    )

    if estimated_nps is not None:

        if estimated_nps >= 50:
            nps_classification = "EXCELLENT"
        elif estimated_nps >= 20:
            nps_classification = "GOOD"
        elif estimated_nps >= 0:
            nps_classification = "NEEDS IMPROVEMENT"
        else:
            nps_classification = "CRITICAL"

        add_rule(
            results,
            silo="service",
            rule_id="6.10",
            title=(
                "Estimated NPS is "
                f"{nps_classification.lower()}"
            ),
            analysis=(
                f"Official Rule 6.10 estimates NPS from referral "
                f"frequency and quality consistency. The estimated "
                f"NPS is {estimated_nps:.1f}."
            ),
            evidence_question_ids=[
                39,
                40
            ],
            recommendations=(
                [
                    "Treat the negative estimated NPS as a customer-satisfaction crisis and investigate root causes immediately."
                ]
                if estimated_nps < 0
                else []
            ),
            classification=nps_classification,
            kind="estimated_rule",
            confidence="medium"
        )

    # =====================================================
    # SERVICE/RISK — CROSS-RULE CS.23
    # QUALITY CONSISTENCY <= 2
    # =====================================================

    quality_consistency_score = numeric_score(
        answers,
        39
    )

    if (
        quality_consistency_score is not None
        and quality_consistency_score <= 2
    ):

        add_rule(
            results,
            silo="risk",
            rule_id="CS.23-REPUTATION",
            title="Service inconsistency creates high reputational risk",
            analysis=(
                "Service quality consistency is rated 2 or lower. "
                "Under official Cross-Rule CS.23 for the superyacht "
                "industry, this creates reputational-damage exposure "
                "with Likely likelihood and Major impact, producing "
                "a HIGH risk rating."
            ),
            evidence_question_ids=[
                39
            ],
            recommendations=[
                "Implement service-quality safeguards before a high-visibility service failure occurs."
            ],
            classification="HIGH",
            kind="rule",
            confidence="high"
        )


    # =====================================================
    # SERVICE/RISK — CROSS-RULE CS.23
    # referral <=2 AND repeat customers 25-50%
    # =====================================================

    referral = answer_text(
        answers,
        40
    )

    try:
        referral_score = int(
            float(
                referral
            )
        )
    except Exception:
        referral_score = None

    if (
        referral_score is not None
        and referral_score <= 2
        and "25-50" in repeat_customers
    ):
        results["service"].append(
            make_rule_result(
                rule_id="CS.23",
                silo="service",
                title="Customers return but referral advocacy is weak",
                analysis=(
                    "Repeat customers are in the 25-50% range while "
                    "referral frequency is 2 or lower. The official "
                    "cross-rule identifies a gap between retention "
                    "and advocacy."
                ),
                evidence_question_ids=[
                    38,
                    40
                ],
                recommendations=[
                    "Investigate why repeat customers are not referring the business through structured feedback and exit interviews."
                ],
                classification="REFERRAL GAP"
            )
        )

        results["risk"].append(
            make_rule_result(
                rule_id="CS.23",
                silo="risk",
                title="Low referral advocacy creates competitive displacement risk",
                analysis=(
                    "The combination of moderate repeat business and "
                    "low referral frequency triggers the official "
                    "service-to-risk cross-rule."
                ),
                evidence_question_ids=[
                    38,
                    40
                ],
                recommendations=[
                    "Identify the causes of low advocacy and strengthen the customer experience factors that drive referrals."
                ],
                classification="RISK"
            )
        )

    # =====================================================
    # RISK — RULES 7.4, 7.5, 7.6
    # ISO 31000 SYSTEMATIC RISK IDENTIFICATION
    # =====================================================

    generated_risks = []


    def add_generated_risk(
        *,
        result_id,
        title,
        category,
        likelihood,
        impact,
        evidence_ids
    ):

        rating_matrix = {
            ("almost certain", "catastrophic"): "CRITICAL",
            ("likely", "catastrophic"): "CRITICAL",
            ("possible", "catastrophic"): "HIGH",
            ("unlikely", "catastrophic"): "MEDIUM",
            ("rare", "catastrophic"): "MEDIUM",

            ("almost certain", "major"): "HIGH",
            ("likely", "major"): "HIGH",
            ("possible", "major"): "MEDIUM",
            ("unlikely", "major"): "LOW",
            ("rare", "major"): "LOW",

            ("almost certain", "moderate"): "MEDIUM",
            ("likely", "moderate"): "MEDIUM",
            ("possible", "moderate"): "LOW",
            ("unlikely", "moderate"): "LOW",
            ("rare", "moderate"): "LOW"
        }

        rating = rating_matrix.get(
            (
                likelihood.lower(),
                impact.lower()
            ),
            "LOW"
        )

        if rating == "CRITICAL":
            treatment = (
                "AVOID"
                if category.lower() == "compliance"
                else "REDUCE"
            )
        elif rating == "HIGH":
            treatment = "REDUCE"
        elif rating == "MEDIUM":
            treatment = "MONITOR / REDUCE / TRANSFER"
        else:
            treatment = "ACCEPT"

        generated_risks.append({
            "result_id": result_id,
            "title": title,
            "category": category,
            "likelihood": likelihood,
            "impact": impact,
            "rating": rating,
            "treatment": treatment,
            "evidence_ids": evidence_ids
        })


    owner_dependency = answer_lower(
        answers,
        13
    )

    if (
        "heavily owner-dependent" in owner_dependency
        or "owner-dependent" in owner_dependency
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-OWNER-DEPENDENCY",
            title="Single point of failure from owner dependency",
            category="Strategic",
            likelihood="Likely",
            impact="Catastrophic",
            evidence_ids=[
                13
            ]
        )


    if (
        metrics.get("turnover") is not None
        and metrics["turnover"] >= 50
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-TURNOVER-CONTINUITY",
            title="High turnover threatens operational continuity",
            category="Operational",
            likelihood="Almost Certain",
            impact="Major",
            evidence_ids=[
                18
            ]
        )


    if (
        metrics.get("knowledge_concentration") is not None
        and metrics["knowledge_concentration"] > 50
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-KNOWLEDGE-CONCENTRATION",
            title="Critical knowledge is concentrated in one person",
            category="Operational",
            likelihood="Possible",
            impact="Major",
            evidence_ids=[
                20
            ]
        )


    if vendor_backup == "no":
        add_generated_risk(
            result_id="7.4/7.5/7.6-VENDOR-SINGLE-POINT",
            title="Vendor single point of failure",
            category="Operational",
            likelihood="Unlikely",
            impact="Major",
            evidence_ids=[
                27
            ]
        )


    if (
        metrics.get("revenue_concentration_midpoint") is not None
        and metrics["revenue_concentration_midpoint"] >= 50
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-REVENUE-CONCENTRATION",
            title="Revenue concentration in a single customer",
            category="Financial",
            likelihood="Possible",
            impact="Catastrophic",
            evidence_ids=[
                28
            ]
        )


    if answer_lower(
        answers,
        29
    ) == "yes":
        add_generated_risk(
            result_id="7.4/7.5/7.6-FINANCIAL-WASTE",
            title="Financial waste is eroding profitability",
            category="Financial",
            likelihood="Likely",
            impact="Moderate",
            evidence_ids=[
                29
            ]
        )


    if (
        metrics.get("inbound_midpoint") is not None
        and metrics["inbound_midpoint"] < 30
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-OUTBOUND-DEPENDENCE",
            title="Over-reliance on outbound sales weakens brand resilience",
            category="Strategic",
            likelihood="Likely",
            impact="Moderate",
            evidence_ids=[
                31
            ]
        )


    if (
        metrics.get("repeat_customer_midpoint") is not None
        and metrics["repeat_customer_midpoint"] < 25
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-CUSTOMER-RETENTION",
            title="Low customer retention threatens revenue",
            category="Financial",
            likelihood="Almost Certain",
            impact="Major",
            evidence_ids=[
                38
            ]
        )


    if "no formal process" in answer_lower(
        answers,
        44
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-SANCTIONS",
            title="Sanctions violation risk from absent screening",
            category="Compliance",
            likelihood="Possible",
            impact="Catastrophic",
            evidence_ids=[
                44
            ]
        )


    if answer_lower(
        answers,
        45
    ) == "no":
        add_generated_risk(
            result_id="7.4/7.5/7.6-AML",
            title="AML compliance failure risk",
            category="Compliance",
            likelihood="Possible",
            impact="Major",
            evidence_ids=[
                45
            ]
        )


    if answer_lower(
        answers,
        46
    ) == "no":
        add_generated_risk(
            result_id="7.4/7.5/7.6-PI-COVER",
            title="Inadequate Professional Indemnity coverage",
            category="Financial",
            likelihood="Unlikely",
            impact="Catastrophic",
            evidence_ids=[
                46
            ]
        )


    if (
        "<3" in answer_lower(
            answers,
            48
        )
        or "under 3" in answer_lower(
            answers,
            48
        )
    ):
        add_generated_risk(
            result_id="7.4/7.5/7.6-CASH-RUNWAY",
            title="Insufficient cash runway for market disruption",
            category="Financial",
            likelihood="Possible",
            impact="Catastrophic",
            evidence_ids=[
                48
            ]
        )


    for risk in generated_risks:

        add_rule(
            results,
            silo="risk",
            rule_id=risk["result_id"],
            title=risk["title"],
            analysis=(
                f"ISO 31000 assigns this risk "
                f"{risk['likelihood']} likelihood and "
                f"{risk['impact']} impact. The official matrix "
                f"therefore rates it {risk['rating']}."
            ),
            evidence_question_ids=risk["evidence_ids"],
            recommendations=[
                f"Apply the official {risk['treatment']} treatment response."
            ],
            classification=risk["rating"]
        )


    # =====================================================
    # RISK — RULE 7.1 CONTRACTOR LIABILITY BOWTIE
    # =====================================================

    contractor_insurance = answer_lower(
        answers,
        43
    )

    pi_cover = answer_lower(
        answers,
        46
    )

    vendor_backup_for_risk = answer_lower(
        answers,
        27
    )


    contractor_barrier = None

    if contractor_insurance == "yes":
        contractor_barrier = "STRONG"
    elif "sometimes" in contractor_insurance:
        contractor_barrier = "WEAK"
    elif contractor_insurance == "no":
        contractor_barrier = "ABSENT"

    if contractor_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.1-CONTRACTOR-INSURANCE",
            title=(
                "Contractor insurance verification barrier is "
                f"{contractor_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.1 classifies subcontractor "
                "insurance verification as "
                f"{contractor_barrier}."
            ),
            evidence_question_ids=[
                43
            ],
            recommendations=(
                [
                    "Mandate contractor insurance verification immediately."
                ]
                if contractor_barrier == "ABSENT"
                else []
            ),
            classification=contractor_barrier
        )


    vendor_vetting_barrier = None

    if vendor_backup_for_risk:

        if "for all critical services" in vendor_backup_for_risk:
            vendor_vetting_barrier = "STRONG"

        elif "for some" in vendor_backup_for_risk:
            vendor_vetting_barrier = "WEAK"

        elif vendor_backup_for_risk == "no":
            vendor_vetting_barrier = "ABSENT"


    if vendor_vetting_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.1-VENDOR-VETTING",
            title=(
                "Vendor vetting barrier is "
                f"{vendor_vetting_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.1 uses Tier-2 vendor availability "
                "as a contractor-liability prevention barrier."
            ),
            evidence_question_ids=[
                27
            ],
            recommendations=[],
            classification=vendor_vetting_barrier
        )


    pi_barrier = None

    if pi_cover == "yes":
        pi_barrier = "STRONG"
    elif "partial" in pi_cover:
        pi_barrier = "MODERATE"
    elif pi_cover == "no":
        pi_barrier = "ABSENT"

    if pi_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.1-PI-COVER",
            title=(
                "Professional Indemnity recovery barrier is "
                f"{pi_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.1 classifies PI insurance coverage "
                f"as a {pi_barrier} recovery barrier."
            ),
            evidence_question_ids=[
                46
            ],
            recommendations=(
                [
                    "Review Professional Indemnity limits against the largest contract immediately."
                ]
                if pi_barrier in {
                    "ABSENT",
                    "MODERATE"
                }
                else []
            ),
            classification=pi_barrier
        )


    # =====================================================
    # RISK — RULE 7.2 SANCTIONS / UBO BOWTIE
    # =====================================================

    sanctions = answer_lower(
        answers,
        44
    )

    ubo = answer_lower(
        answers,
        45
    )


    sanctions_barrier = None

    if "automated" in sanctions:
        sanctions_barrier = "STRONG"
    elif "periodic manual" in sanctions:
        sanctions_barrier = "MODERATE"
    elif "onboarding only" in sanctions:
        sanctions_barrier = "WEAK"
    elif "no formal process" in sanctions:
        sanctions_barrier = "ABSENT"

    if sanctions_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.2-SANCTIONS",
            title=(
                "Sanctions screening barrier is "
                f"{sanctions_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.2 classifies the current "
                "sanctions-screening control as "
                f"{sanctions_barrier}."
            ),
            evidence_question_ids=[
                44
            ],
            recommendations=(
                [
                    "Implement automated sanctions screening immediately."
                ]
                if sanctions_barrier == "ABSENT"
                else []
            ),
            classification=sanctions_barrier
        )


    ubo_barrier = None

    if (
        "yes, always" in ubo
        or ubo == "always"
    ):
        ubo_barrier = "STRONG"
    elif (
        "occasionally" in ubo
        or "only if required by bank" in ubo
    ):
        ubo_barrier = "WEAK"
    elif ubo == "no":
        ubo_barrier = "ABSENT"

    if ubo_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.2-UBO",
            title=(
                "UBO verification barrier is "
                f"{ubo_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.2 classifies current UBO "
                f"verification as a {ubo_barrier} prevention barrier."
            ),
            evidence_question_ids=[
                45
            ],
            recommendations=(
                [
                    "Introduce consistent UBO verification immediately."
                ]
                if ubo_barrier in {
                    "WEAK",
                    "ABSENT"
                }
                else []
            ),
            classification=ubo_barrier
        )


    if (
        sanctions_barrier == "ABSENT"
        or ubo_barrier == "ABSENT"
    ):
        add_rule(
            results,
            silo="risk",
            rule_id="7.2-CRITICAL-EXPOSURE",
            title="Sanctions risk exposure is critical",
            analysis=(
                "Sanctions screening is absent or UBO verification "
                "is absent. Official Rule 7.2 therefore classifies "
                "sanctions exposure as CRITICAL."
            ),
            evidence_question_ids=[
                44,
                45
            ],
            recommendations=[
                "Implement automated screening and formal ownership verification immediately."
            ],
            classification="CRITICAL"
        )

    # =====================================================
    # RISK — RULE 7.3 FINANCIAL DISTRESS BOWTIE
    # =====================================================

    runway_value = answer_lower(
        answers,
        48
    )

    if (
        "12+" in runway_value
        or "over 12" in runway_value
    ):
        reserve_barrier = "STRONG"
    elif "6-12" in runway_value:
        reserve_barrier = "MODERATE"
    elif "3-6" in runway_value:
        reserve_barrier = "WEAK"
    elif (
        "<3" in runway_value
        or "under 3" in runway_value
    ):
        reserve_barrier = "ABSENT"
    else:
        reserve_barrier = None


    concentration_value = answer_lower(
        answers,
        28
    )

    if (
        "<5" in concentration_value
        or "under 5" in concentration_value
    ):
        diversification_barrier = "STRONG"
    elif "5-15" in concentration_value:
        diversification_barrier = "MODERATE"
    elif (
        "25-50" in concentration_value
        or "50-75" in concentration_value
        or "75-100" in concentration_value
        or ">25" in concentration_value
    ):
        diversification_barrier = "WEAK"
    else:
        diversification_barrier = None


    recurring_value = answer_lower(
        answers,
        30
    )

    if (
        ">75" in recurring_value
        or "75-100" in recurring_value
    ):
        recurring_barrier = "STRONG"
    elif "50-75" in recurring_value:
        recurring_barrier = "MODERATE"
    elif "25-50" in recurring_value:
        recurring_barrier = "WEAK"
    elif (
        "<25" in recurring_value
        or "under 25" in recurring_value
    ):
        recurring_barrier = "ABSENT"
    else:
        recurring_barrier = None


    if reserve_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.3-RESERVES",
            title=(
                "Financial reserve barrier is "
                f"{reserve_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.3 classifies operational cash "
                f"runway as a {reserve_barrier} insolvency-prevention barrier."
            ),
            evidence_question_ids=[
                48
            ],
            recommendations=[],
            classification=reserve_barrier
        )


    if diversification_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.3-DIVERSIFICATION",
            title=(
                "Revenue diversification barrier is "
                f"{diversification_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.3 classifies revenue diversification "
                f"as a {diversification_barrier} prevention barrier."
            ),
            evidence_question_ids=[
                28
            ],
            recommendations=[],
            classification=diversification_barrier
        )


    if recurring_barrier:

        add_rule(
            results,
            silo="risk",
            rule_id="7.3-RECURRING-REVENUE",
            title=(
                "Recurring revenue barrier is "
                f"{recurring_barrier.lower()}"
            ),
            analysis=(
                "Official Rule 7.3 classifies recurring revenue "
                f"as a {recurring_barrier} resilience barrier."
            ),
            evidence_question_ids=[
                30
            ],
            recommendations=[],
            classification=recurring_barrier
        )


    if (
        reserve_barrier == "ABSENT"
        and metrics.get(
            "revenue_concentration_midpoint"
        ) is not None
        and metrics[
            "revenue_concentration_midpoint"
        ] > 50
    ):
        add_rule(
            results,
            silo="risk",
            rule_id="7.3-CRITICAL-DISTRESS",
            title="Financial distress risk is critical",
            analysis=(
                "Operational runway is under three months and "
                "customer concentration exceeds 50%. Official "
                "Rule 7.3 therefore classifies residual financial "
                "distress risk as CRITICAL."
            ),
            evidence_question_ids=[
                28,
                48
            ],
            recommendations=[
                "Implement an emergency cash-conservation plan."
            ],
            classification="CRITICAL"
        )



    referral_policy = answer_lower(
        answers,
        47
    )


    aml_classification = None
    aml_control_maturity = None
    aml_recommendations = []


    screening_automated_or_periodic = (
        "automated" in sanctions
        or "periodic manual" in sanctions
    )

    screening_periodic = (
        "periodic manual" in sanctions
    )

    referral_policy_written = (
        "written" in referral_policy
        or (
            "yes" in referral_policy
            and "transparent" in referral_policy
        )
    )


    # ROBUST
    if (
        (
            "yes, always" in ubo
            or ubo == "always"
        )
        and screening_automated_or_periodic
        and referral_policy_written
    ):
        aml_control_maturity = "ROBUST"
        aml_classification = "MEDIUM"

        aml_recommendations = [
            "Maintain robust AML, UBO and screening controls and review them regularly."
        ]


    # ADEQUATE
    elif (
        "occasionally" in ubo
        and screening_periodic
    ):
        aml_control_maturity = "ADEQUATE"
        aml_classification = "HIGH"

        aml_recommendations = [
            "Strengthen UBO verification and screening controls to move from adequate to robust AML maturity."
        ]


    # MINIMAL
    elif (
        "only if required by bank" in ubo
        or ubo == "no"
        or "onboarding only" in sanctions
        or "no formal process" in sanctions
    ):
        aml_control_maturity = "MINIMAL"
        aml_classification = "CRITICAL"

        aml_recommendations = [
            "Engage a compliance specialist and strengthen AML, UBO and screening controls immediately."
        ]


    if aml_classification:

        results["risk"].append(
            make_rule_result(
                rule_id="7.8",
                silo="risk",
                title=(
                    f"AML control maturity is "
                    f"{aml_control_maturity.lower()} and "
                    f"actual AML risk is "
                    f"{aml_classification.lower()}"
                ),
                analysis=(
                    f"The official PULSE AML rule classifies the "
                    f"current control environment as "
                    f"{aml_control_maturity}. Actual AML risk is "
                    f"therefore {aml_classification}."
                ),
                evidence_question_ids=[
                    question_id
                    for question_id in [
                        44,
                        45,
                        47
                    ]
                    if answer_text(
                        answers,
                        question_id
                    )
                ],
                recommendations=aml_recommendations,
                classification=aml_classification,
                kind="rule",
                confidence="high"
            )
        )


    sanctions_score = None
    ubo_score = None
    contractor_score = None
    referral_policy_score = None


    # -----------------------------------------------------
    # Sanctions screening = 35%
    # -----------------------------------------------------

    if "automated" in sanctions:
        sanctions_score = 100

    elif "periodic manual" in sanctions:
        sanctions_score = 60

    elif "onboarding only" in sanctions:
        sanctions_score = 30

    elif "no formal process" in sanctions:
        sanctions_score = 0


    # -----------------------------------------------------
    # UBO verification = 35%
    # -----------------------------------------------------

    if (
        "yes, always" in ubo
        or ubo == "always"
    ):
        ubo_score = 100

    elif "occasionally" in ubo:
        ubo_score = 40

    elif "only if required by bank" in ubo:
        ubo_score = 30

    elif ubo == "no":
        ubo_score = 0


    # -----------------------------------------------------
    # Contractor insurance = 15%
    # -----------------------------------------------------

    if contractor_insurance == "yes":
        contractor_score = 100

    elif "sometimes" in contractor_insurance:
        contractor_score = 50

    elif contractor_insurance == "no":
        contractor_score = 0


    # -----------------------------------------------------
    # Referral fee policy = 15%
    # -----------------------------------------------------

    if (
        "written" in referral_policy
        and "transparent" in referral_policy
    ):
        referral_policy_score = 100

    elif (
        "yes" in referral_policy
        and "transparent" in referral_policy
    ):
        # Current assessment wording:
        # "Yes, transparent"
        referral_policy_score = 100

    elif "informal" in referral_policy:
        referral_policy_score = 50

    elif (
        "no policy" in referral_policy
        or referral_policy == "no"
    ):
        referral_policy_score = 0


    compliance_components = [
        sanctions_score,
        ubo_score,
        contractor_score,
        referral_policy_score
    ]

    if all(
        score is not None
        for score in compliance_components
    ):

        compliance_maturity_score = (
            sanctions_score * 0.35
            + ubo_score * 0.35
            + contractor_score * 0.15
            + referral_policy_score * 0.15
        )

        if compliance_maturity_score >= 75:
            compliance_classification = "ADVANCED"

        elif compliance_maturity_score >= 50:
            compliance_classification = "DEVELOPING"

        elif compliance_maturity_score >= 25:
            compliance_classification = "BASIC"

        else:
            compliance_classification = "NON-EXISTENT"


        results["risk"].append(
            make_rule_result(
                rule_id="7.7",
                silo="risk",
                title=(
                    "Compliance maturity is "
                    f"{compliance_classification.lower()}"
                ),
                analysis=(
                    "The official PULSE compliance maturity model "
                    "combines sanctions screening, UBO verification, "
                    "contractor insurance controls and referral-fee "
                    "policy using the prescribed 35%, 35%, 15% and "
                    "15% weights."
                ),
                evidence_question_ids=[
                    43,
                    44,
                    45,
                    47
                ],
                recommendations=(
                    [
                        "Address the weakest compliance controls before expanding risk exposure."
                    ]
                    if compliance_classification
                    != "NON-EXISTENT"
                    else
                    [
                        "Treat the compliance-control deficiency as an immediate priority and establish formal screening, ownership-verification and governance controls."
                    ]
                ),
                classification=compliance_classification,
                kind="rule",
                confidence="high"
            )
        )

    runway = answer_lower(
        answers,
        48
    )

    runway_classification = None

    if (
        "12+" in runway
        or "over 12" in runway
    ):
        runway_classification = "STRONG"

    elif "6-12" in runway:
        runway_classification = "MODERATE"

    elif "3-6" in runway:
        runway_classification = "WEAK"

    elif (
        "<3" in runway
        or "under 3" in runway
    ):
        runway_classification = "CRITICAL"

    revenue_concentration_value = answer_lower(
        answers,
        28
    )

    recurring_revenue_value = answer_lower(
        answers,
        30
    )

    revenue_concentration_high = (
        "50-75" in revenue_concentration_value
        or "75-100" in revenue_concentration_value
        or ">75" in revenue_concentration_value
        or ">50" in revenue_concentration_value
        or "over 50" in revenue_concentration_value
    )

    recurring_below_25 = (
        "<25" in recurring_revenue_value
        or "under 25" in recurring_revenue_value
        or "0-25" in recurring_revenue_value
    )

    perfect_storm_financial_risk = (
        runway_classification in {
            "WEAK",
            "CRITICAL"
        }
        and (
            revenue_concentration_high
            or recurring_below_25
        )
    )


    if perfect_storm_financial_risk:

        results["risk"].append(
            make_rule_result(
                rule_id="7.9",
                silo="risk",
                title="Operational resilience risk is critical",
                analysis=(
                    "Operational runway is weak or critical and is "
                    "combined with an additional financial resilience "
                    "trigger. Under the official PULSE resilience rule, "
                    "the risk escalates to CRITICAL."
                ),
                evidence_question_ids=[
                    question_id
                    for question_id in [
                        28,
                        30,
                        48
                    ]
                    if answer_text(
                        answers,
                        question_id
                    )
                ],
                recommendations=[
                    "Build cash reserves as a priority and strengthen financial contingency planning."
                ],
                classification="CRITICAL",
                kind="rule",
                confidence="high"
            )
        )

    elif runway_classification:

        if runway_classification == "STRONG":

            recommendation = (
                "Maintain cash resilience and preserve sufficient reserves for extended market disruption."
            )

        elif runway_classification == "MODERATE":

            recommendation = (
                "Maintain sufficient liquidity for typical market cycles and monitor runway."
            )

        elif runway_classification == "WEAK":

            recommendation = (
                "Build cash reserves as a priority."
            )

        else:

            recommendation = (
                "Implement emergency financial measures immediately."
            )


        results["risk"].append(
            make_rule_result(
                rule_id="7.9",
                silo="risk",
                title=(
                    "Operational resilience is "
                    f"{runway_classification.lower()}"
                ),
                analysis=(
                    f"The reported operational runway is "
                    f"{answer_text(answers, 48)}. Under the "
                    f"official PULSE operational-resilience thresholds "
                    f"this is classified as "
                    f"{runway_classification}."
                ),
                evidence_question_ids=[
                    48
                ],
                recommendations=[
                    recommendation
                ],
                classification=runway_classification,
                kind="rule",
                confidence="high"
            )
        )


    concentration_over_50 = (
        "50-75" in concentration
        or "75-100" in concentration
        or ">50" in concentration
        or "over 50" in concentration
    )

    outbound_dependent = (
        "0-20" in inbound
        or "20-40" in inbound
    )

    if (
        concentration_over_50
        and outbound_dependent
    ):
        results["marketing"].append(
            make_rule_result(
                rule_id="CS.22-SALES-SCALABILITY",
                silo="marketing",
                title="Knowledge concentration limits sales scalability",
                analysis=(
                    "More than 50% of critical client relationships "
                    "or technical expertise is concentrated in one "
                    "individual while lead generation is outbound "
                    "dependent. The official cross-rule identifies "
                    "a sales scalability constraint."
                ),
                evidence_question_ids=[
                    20,
                    31
                ],
                recommendations=[
                    "Document expert knowledge into a sales playbook to enable team selling."
                ],
                classification="SCALABILITY RISK",
                kind="rule",
                confidence="high"
            )
        )

    # =====================================================
    # CROSS-RULE CS.4
    # HR → EFFICIENCY → SERVICE
    # =====================================================

    if (
        metrics.get(
            "turnover"
        )
        is not None
        and metrics[
            "turnover"
        ] >= 50
    ):

        add_rule(
            results,
            silo="operations",
            rule_id="CS.4",
            title="High turnover is reducing process stability",
            analysis=(
                "Employee turnover is at least 50%. Official "
                "Cross-Rule CS.4 applies a 40% deterioration to "
                "process stability."
            ),
            evidence_question_ids=[
                18
            ],
            recommendations=[
                "Stabilise the workforce while documenting critical operational processes."
            ],
            classification="HIGH",
            kind="estimated_rule"
        )

        add_rule(
            results,
            silo="service",
            rule_id="CS.4",
            title="High turnover is degrading service reliability and assurance",
            analysis=(
                "Turnover of at least 50% triggers the official "
                "HR-Efficiency-Service Quality cascade, reducing "
                "service reliability and assurance."
            ),
            evidence_question_ids=[
                18
            ],
            recommendations=[
                "Run workforce-retention and service-standardisation workstreams in parallel."
            ],
            classification="HIGH",
            kind="estimated_rule"
        )

        # =====================================================
    # CROSS-RULE CS.6
    # EFFICIENCY → FINANCIAL WASTE
    # =====================================================

    estimated_waste_pct = 0
    waste_evidence_ids = []

    sop = answer_lower(
        answers,
        21
    )

    if sop == "no":
        estimated_waste_pct += 10
        waste_evidence_ids.append(
            21
        )

    if contains_any(
        answer_lower(
            answers,
            9
        ),
        [
            "a lot",
            "high"
        ]
    ):
        estimated_waste_pct += 12
        waste_evidence_ids.append(
            9
        )

    if contains_any(
        answer_lower(
            answers,
            5
        ),
        [
            "critical impact"
        ]
    ):
        estimated_waste_pct += 8
        waste_evidence_ids.append(
            5
        )

    if (
        metrics.get(
            "turnover"
        )
        is not None
        and metrics[
            "turnover"
        ] >= 50
    ):
        estimated_waste_pct += 15
        waste_evidence_ids.append(
            18
        )

    metrics[
        "cross_silo_estimated_waste_pct"
    ] = estimated_waste_pct

    if estimated_waste_pct >= 25:

        add_rule(
            results,
            silo="financial",
            rule_id="CS.6",
            title="Cross-silo operational waste is high",
            analysis=(
                f"Official Cross-Rule CS.6 aggregates the current "
                f"inefficiency signals into an estimated waste "
                f"level of {estimated_waste_pct}% of revenue. "
                f"This is a rule-derived estimate, not a measured "
                f"financial result."
            ),
            evidence_question_ids=waste_evidence_ids,
            recommendations=[
                "Prioritise an operational excellence programme around the largest identified waste sources."
            ],
            classification="HIGH",
            kind="estimated_rule",
            confidence="medium"
        )

    # =====================================================
    # RISK — RULE 7.10 ENTERPRISE RISK SCORE
    # =====================================================

    risk_findings = results.get(
        "risk",
        []
    )

    critical_count = sum(
        1
        for item in risk_findings
        if str(
            item.get(
                "classification"
            )
            or ""
        ).upper() == "CRITICAL"
    )

    high_count = sum(
        1
        for item in risk_findings
        if str(
            item.get(
                "classification"
            )
            or ""
        ).upper() == "HIGH"
    )


    resilience_score_lookup = {
        "STRONG": 100,
        "MODERATE": 70,
        "WEAK": 40,
        "CRITICAL": 0
    }


    resilience_findings = [
        item
        for item in risk_findings
        if str(
            item.get(
                "rule_id"
            )
            or ""
        ) == "7.9"
    ]

    resilience_class = (
        str(
            resilience_findings[-1].get(
                "classification"
            )
            or ""
        ).upper()
        if resilience_findings
        else ""
    )

    resilience_score = (
        resilience_score_lookup.get(
            resilience_class
        )
    )


    if (
        "compliance_maturity_score" in locals()
        and resilience_score is not None
    ):

        critical_risk_component = min(
            critical_count / 5,
            1.0
        ) * 100

        high_risk_component = min(
            high_count / 10,
            1.0
        ) * 100

        # The source expresses the score as 1.0 minus a
        # weighted risk burden. Compliance and resilience
        # are positive controls, so convert them to deficits
        # before including them in that risk burden.
        risk_burden = (
            critical_risk_component * 0.25
            + high_risk_component * 0.15
            + (
                100
                - compliance_maturity_score
            ) * 0.30
            + (
                100
                - resilience_score
            ) * 0.30
        )

        enterprise_risk_score = max(
            0.0,
            100.0
            - risk_burden
        )

        enterprise_at_risk = (
            enterprise_risk_score < 50
        )

        add_rule(
            results,
            silo="risk",
            rule_id="7.10",
            title=(
                "Enterprise is at risk"
                if enterprise_at_risk
                else "Enterprise risk score calculated"
            ),
            analysis=(
                f"Official Rule 7.10 produces an enterprise-risk "
                f"score of {enterprise_risk_score:.1f}/100 from "
                f"critical risks, high risks, compliance maturity "
                f"and operational resilience."
            ),
            evidence_question_ids=list(
                dict.fromkeys(
                    question_id
                    for finding in risk_findings
                    for question_id in finding.get(
                        "evidence_question_ids",
                        []
                    )
                )
            ),
            recommendations=(
                [
                    "Conduct a board-level risk review immediately."
                ]
                if enterprise_at_risk
                else []
            ),
            classification=(
                "ENTERPRISE AT RISK"
                if enterprise_at_risk
                else None
            ),
            kind="estimated_rule",
            confidence="medium"
        )

    return results
    
# =========================================================
# INTELLIGENT SILO FINDINGS
# =========================================================

def build_intelligent_silo_findings(
    *,
    silo_name: str,
    answers: Dict[str, Any],
    official_rule_results: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    OpenAI may EXPLAIN official deterministic rule results.

    It may not invent, soften, strengthen or replace
    official classifications.
    """

    semantic_answers = build_answer_evidence(
        answers,
        silo_name
    )

    silo_rules = (
        official_rule_results.get(
            silo_name,
            []
        )
    )

    evidence = {
        "silo": silo_name,
        "direct_assessment_evidence": semantic_answers,
        "official_rule_results": silo_rules
    }

    instructions = """
You are the user-facing explanation layer for PULSE.

The OFFICIAL ontology rules have ALREADY been evaluated
deterministically by the backend.

You are NOT the rule engine.

=========================================================
ABSOLUTE RULE PRIORITY
=========================================================

1. official_rule_results are authoritative.

2. NEVER change an official classification.

Examples:

If the official rule says:
classification = "WEAK"

you MUST NOT call it:
- moderate
- adequate
- acceptable
- reasonably healthy

If the official rule says:
classification = "CRITICAL"

you MUST NOT soften it to:
- notable
- potential
- moderate
- incomplete

3. Never invent a new formal classification.

4. Never calculate a new metric or score.

5. Never override an official rule result with your own judgement.

6. If an official rule result conflicts with a casual interpretation
   of a direct answer, the official rule result wins.

=========================================================
DIRECT EVIDENCE
=========================================================

7. Direct assessment evidence may be used to explain context.

8. Every factual statement must be supported by either:
   - official_rule_results; or
   - direct_assessment_evidence.

9. Preserve exact ranges.

Do not convert:
25-50%
into:
37.5%.

10. Do not invent missing facts.

=========================================================
FINDING CONSTRUCTION
=========================================================

11. Every official rule result MUST appear in the final findings.

12. Preserve:
   - rule_id
   - classification
   - evidence_question_ids
   - confidence
   - kind

13. You may combine closely related official rule results into one
    finding ONLY if no classification is lost.

14. Do NOT create additional user-facing findings from direct
    assessment evidence unless an official deterministic rule
    result exists.

    Direct assessment evidence may ONLY be used to explain an
    existing official rule result.

    Every user-facing finding MUST contain at least one valid
    rule_id from official_rule_results.

15. Recommendations must be consistent with the official rule.

16. Use professional British English.

Return ONLY valid JSON:

{
  "findings": [
    {
      "title": "finding title",
      "analysis": "explanation",
      "rule_ids": ["2.8", "CS.5"],
      "classification": "CRITICAL",
      "kind": "rule",
      "confidence": "high",
      "evidence_question_ids": [18, 20],
      "recommendations": [
        "specific action"
      ]
    }
  ]
}
""".strip()

    try:

        response = openai_client.responses.create(
            model=OPENAI_ANALYSIS_MODEL,
            instructions=instructions,
            input=json.dumps(
                evidence,
                ensure_ascii=False,
                default=str
            )
        )

        raw = str(
            response.output_text
            or ""
        ).strip()

        if raw.startswith("```"):
            raw = (
                raw
                .strip("`")
                .strip()
            )

            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        parsed = json.loads(
            raw
        )

        findings = parsed.get(
            "findings"
        )

        if not isinstance(
            findings,
            list
        ):
            findings = []

        valid_question_ids = {
            int(item["question_id"])
            for item in semantic_answers
        }


        # =================================================
        # INCLUDE OFFICIAL CROSS-SILO RULE EVIDENCE
        # =================================================
        #
        # A deterministic rule may legitimately use a
        # question outside the silo's direct evidence scope.
        #
        # Example:
        #
        # Rule 3.9 generates Strategy / People / Service
        # findings from Q21 even though Q21 is primarily an
        # Operations assessment question.
        #
        # Those IDs must therefore remain valid.
        # =================================================

        for rule in silo_rules:

            for question_id in (
                rule.get(
                    "evidence_question_ids"
                )
                or []
            ):

                try:

                    valid_question_ids.add(
                        int(
                            question_id
                        )
                    )

                except Exception:

                    continue


        official_rule_ids = {
            str(rule.get("rule_id"))
            for rule in silo_rules
        }

        official_rules_by_id = {
            str(
                rule.get(
                    "rule_id"
                )
            ): rule
            for rule in silo_rules
            if str(
                rule.get(
                    "rule_id"
                )
                or ""
            ).strip()
        }

        clean_findings = []

        for finding in findings:

            if not isinstance(
                finding,
                dict
            ):
                continue

            title = str(
                finding.get("title")
                or ""
            ).strip()

            analysis = str(
                finding.get("analysis")
                or ""
            ).strip()

            if not title or not analysis:
                continue

            evidence_ids = []

            for question_id in (
                finding.get(
                    "evidence_question_ids"
                )
                or []
            ):

                try:
                    question_id = int(
                        question_id
                    )
                except Exception:
                    continue

                if (
                    question_id in valid_question_ids
                    and question_id not in evidence_ids
                ):
                    evidence_ids.append(
                        question_id
                    )

            if not evidence_ids:
                continue

            rule_ids = []

            for rule_id in (
                finding.get(
                    "rule_ids"
                )
                or []
            ):

                rule_id = str(
                    rule_id
                ).strip()

                if (
                    rule_id in official_rule_ids
                    and rule_id not in rule_ids
                ):
                    rule_ids.append(
                        rule_id
                    )

            # =================================================
            # USER-FACING FINDINGS MUST COME FROM AN
            # OFFICIAL DETERMINISTIC ONTOLOGY RULE
            # =================================================

            if not rule_ids:
                continue

            official_classification = None
            official_kind = None
            official_confidence = None

            if rule_ids:

                matched_rules = [
                    official_rules_by_id[
                        rule_id
                    ]
                    for rule_id in rule_ids
                    if rule_id in official_rules_by_id
                ]

                classifications = {
                    str(
                        rule.get(
                            "classification"
                        )
                        or ""
                    ).strip()
                    for rule in matched_rules
                    if str(
                        rule.get(
                            "classification"
                        )
                        or ""
                    ).strip()
                }

                # Do not allow OpenAI to merge official rules
                # with different classifications into one finding.
                if len(
                    classifications
                ) > 1:
                    continue

                if matched_rules:

                    first_rule = matched_rules[
                        0
                    ]

                    official_classification = (
                        first_rule.get(
                            "classification"
                        )
                    )

                    official_kind = (
                        first_rule.get(
                            "kind"
                        )
                        or "rule"
                    )

                    official_confidence = (
                        first_rule.get(
                            "confidence"
                        )
                        or "high"
                    )

            recommendations = [
                str(item).strip()
                for item in (
                    finding.get(
                        "recommendations"
                    )
                    or []
                )
                if str(
                    item or ""
                ).strip()
            ]

            clean_findings.append({
                "title": title,
                "analysis": analysis,
                "rule_ids": rule_ids,

                "classification": (
                    official_classification
                    if rule_ids
                    else None
                ),

                "kind": (
                    official_kind
                    if rule_ids
                    else "direct"
                ),

                "confidence": (
                    official_confidence
                    if rule_ids
                    else "high"
                ),

                "evidence_question_ids": evidence_ids,
                "recommendations": recommendations
            })


        # =================================================
        # GUARANTEE EVERY OFFICIAL RULE APPEARS
        # =================================================
        #
        # If OpenAI accidentally omits an official rule,
        # insert the deterministic rule result directly.
        # =================================================

        represented_rule_ids = {
            rule_id
            for finding in clean_findings
            for rule_id in finding.get(
                "rule_ids",
                []
            )
        }

        for rule in silo_rules:

            rule_id = str(
                rule.get(
                    "rule_id"
                )
                or ""
            )

            if (
                not rule_id
                or rule_id in represented_rule_ids
            ):
                continue

            clean_findings.append({
                "title": rule.get(
                    "title"
                ),
                "analysis": rule.get(
                    "analysis"
                ),
                "rule_ids": [
                    rule_id
                ],
                "classification": rule.get(
                    "classification"
                ),
                "kind": rule.get(
                    "kind"
                ),
                "confidence": rule.get(
                    "confidence"
                ),
                "evidence_question_ids": rule.get(
                    "evidence_question_ids",
                    []
                ),
                "recommendations": rule.get(
                    "recommendations",
                    []
                )
            })


        return {
            "findings": clean_findings
        }


    except Exception as error:

        print(
            "OPENAI SILO ANALYSIS ERROR:",
            {
                "silo": silo_name,
                "error_type": type(
                    error
                ).__name__,
                "error": str(
                    error
                )
            }
        )

        # IMPORTANT:
        # Even if OpenAI fails, official rule results
        # still survive and are shown.
        return {
            "findings": [
                {
                    "title": rule.get(
                        "title"
                    ),
                    "analysis": rule.get(
                        "analysis"
                    ),
                    "rule_ids": [
                        str(
                            rule.get(
                                "rule_id"
                            )
                        )
                    ],
                    "classification": rule.get(
                        "classification"
                    ),
                    "kind": rule.get(
                        "kind"
                    ),
                    "confidence": rule.get(
                        "confidence"
                    ),
                    "evidence_question_ids": rule.get(
                        "evidence_question_ids",
                        []
                    ),
                    "recommendations": rule.get(
                        "recommendations",
                        []
                    )
                }
                for rule in silo_rules
            ]
        }


# =========================================================
# MASTER ENGINE
# =========================================================
def run_full_analysis(
    data: Any
) -> Dict[str, Any]:
    """
    Generate the user-facing PULSE analysis directly from
    the respondent's latest authoritative assessment answers.

    Legacy deterministic silo/cross calculations are available
    only in explicit backend debug mode.
    """

    if not isinstance(
        data,
        dict
    ):
        data = {}


    official_rule_results = (
        evaluate_official_ontology_rules(
            data
        )
    )


    # =====================================================
    # 1. GENERATE USER-FACING SILO ANALYSIS IN PARALLEL
    # =====================================================

    silo_names = list(
        SILO_EVIDENCE_QUESTION_IDS.keys()
    )

    intelligent_silos = {}

    with ThreadPoolExecutor(
        max_workers=4
    ) as executor:

        future_to_silo = {}

        for silo_name in silo_names:

            future = executor.submit(
                build_intelligent_silo_findings,
                silo_name=silo_name,
                answers=data,
                official_rule_results=official_rule_results
            )

            future_to_silo[
                future
            ] = silo_name

        for future in as_completed(
            future_to_silo
        ):

            silo_name = future_to_silo[
                future
            ]

            try:

                silo_result = future.result()

                if (
                    not isinstance(
                        silo_result,
                        dict
                    )
                    or not isinstance(
                        silo_result.get(
                            "findings"
                        ),
                        list
                    )
                ):
                    silo_result = {
                        "findings": []
                    }

                intelligent_silos[
                    silo_name
                ] = silo_result

                print(
                    "PULSE SILO RESULT:",
                    {
                        "silo": silo_name,
                        "finding_count": len(
                            silo_result.get(
                                "findings",
                                []
                            )
                        )
                    }
                )

            except Exception as silo_error:

                print(
                    "SILO INTELLIGENCE ERROR:",
                    {
                        "silo": silo_name,
                        "error_type": (
                            type(
                                silo_error
                            ).__name__
                        ),
                        "error": str(
                            silo_error
                        )
                    }
                )

                intelligent_silos[
                    silo_name
                ] = {
                    "findings": []
                }


    # Restore stable silo ordering because parallel jobs
    # can finish in any order.
    intelligent_silos = {
        silo_name: (
            intelligent_silos.get(
                silo_name,
                {
                    "findings": []
                }
            )
        )
        for silo_name in silo_names
    }

    result = {
        "overall_score": None,
        "silos": intelligent_silos,
        "official_rule_results": official_rule_results
    }


    # =====================================================
    # 3. OPTIONAL LEGACY DEBUG ANALYSIS
    # =====================================================

    include_raw = (
        os.getenv(
            "PULSE_INCLUDE_RAW_ANALYSIS",
            "false"
        )
        .strip()
        .lower()
        == "true"
    )

    if include_raw:

        try:

            raw_silo1 = run_silo1(
                data
            )

            raw_silo2 = run_silo2(
                data
            )

            raw_silo3 = run_silo3(
                data
            )

            raw_silo4 = run_silo4(
                data
            )

            raw_silo5 = run_silo5(
                data,
                silo1=raw_silo1,
                silo4=raw_silo4
            )

            raw_silo6 = run_silo6(
                data,
                silo2=raw_silo2,
                silo3=raw_silo3,
                silo4=raw_silo4
            )

            raw_silo7 = run_silo7(
                data,
                silo4=raw_silo4
            )

            raw_silos = {
                "strategy": raw_silo1,
                "people": raw_silo2,
                "operations": raw_silo3,
                "financial": raw_silo4,
                "marketing": raw_silo5,
                "service": raw_silo6,
                "risk": raw_silo7
            }

            result[
                "raw_silos"
            ] = raw_silos


            try:

                result[
                    "cross_analysis"
                ] = run_cross_analysis(
                    data=data,
                    silo1=raw_silo1,
                    silo2=raw_silo2,
                    silo3=raw_silo3,
                    silo4=raw_silo4,
                    silo5=raw_silo5,
                    silo6=raw_silo6,
                    silo7=raw_silo7
                )

            except Exception as cross_error:

                print(
                    "DEBUG CROSS ANALYSIS ERROR:",
                    {
                        "error_type": (
                            type(
                                cross_error
                            ).__name__
                        ),
                        "error": str(
                            cross_error
                        )
                    }
                )

                result[
                    "cross_analysis"
                ] = None


        except Exception as raw_error:

            print(
                "DEBUG RAW ANALYSIS ERROR:",
                {
                    "error_type": (
                        type(
                            raw_error
                        ).__name__
                    ),
                    "error": str(
                        raw_error
                    )
                }
            )


    return result

# =========================================================
# INCREMENTAL ANALYSIS
# =========================================================

def run_incremental_analysis(
    data: Any,
    changed_question_ids,
    previous_analysis: Any = None
) -> Dict[str, Any]:
    """
    Reanalyse ONLY silos affected by the changed questions.

    Existing findings for unrelated silos are preserved.

    Example:
        Q38 belongs to:
        - marketing
        - service
        - risk

        Therefore all three are regenerated automatically,
        while strategy, people, operations and financial
        remain unchanged.
    """

    if not isinstance(
        data,
        dict
    ):
        data = {}

    official_rule_results = (
        evaluate_official_ontology_rules(
            data
        )
    )

    if not isinstance(
        previous_analysis,
        dict
    ):
        previous_analysis = {}

    previous_silos = previous_analysis.get(
        "silos"
    )

    if not isinstance(
        previous_silos,
        dict
    ):
        previous_silos = {}

    affected_silos = affected_silos_for_questions(
        changed_question_ids
    )

    print(
        "PULSE INCREMENTAL ANALYSIS:",
        {
            "changed_question_ids": list(
                changed_question_ids or []
            ),
            "affected_silos": affected_silos
        }
    )

    # If there is no usable previous analysis, build everything.
    if not previous_silos:
        return run_full_analysis(
            data
        )

    # Start from the previous analysis so unrelated silos
    # remain untouched.
    merged_silos = {}

    for silo_name in SILO_EVIDENCE_QUESTION_IDS.keys():

        existing = previous_silos.get(
            silo_name
        )

        if isinstance(
            existing,
            dict
        ):
            merged_silos[
                silo_name
            ] = existing
        else:
            merged_silos[
                silo_name
            ] = {
                "findings": []
            }

    if not affected_silos:
        return {
            "overall_score": None,
            "silos": merged_silos,
            "official_rule_results": official_rule_results,
            "updated_silos": []
        }

    # Regenerate only affected silos.
    max_workers = min(
        4,
        len(
            affected_silos
        )
    )

    with ThreadPoolExecutor(
        max_workers=max_workers
    ) as executor:

        future_to_silo = {}

        for silo_name in affected_silos:

            future = executor.submit(
                build_intelligent_silo_findings,
                silo_name=silo_name,
                answers=data,
                official_rule_results=official_rule_results
            )

            future_to_silo[
                future
            ] = silo_name

        for future in as_completed(
            future_to_silo
        ):

            silo_name = future_to_silo[
                future
            ]

            try:
                silo_result = future.result()

                if (
                    isinstance(
                        silo_result,
                        dict
                    )
                    and isinstance(
                        silo_result.get(
                            "findings"
                        ),
                        list
                    )
                ):
                    merged_silos[
                        silo_name
                    ] = silo_result

                else:
                    print(
                        "INCREMENTAL SILO INVALID RESULT:",
                        silo_name
                    )

            except Exception as silo_error:

                # IMPORTANT:
                # Do not destroy the previous valid analysis
                # just because one OpenAI request failed.
                print(
                    "INCREMENTAL SILO ANALYSIS ERROR:",
                    {
                        "silo": silo_name,
                        "error_type": type(
                            silo_error
                        ).__name__,
                        "error": str(
                            silo_error
                        )
                    }
                )

    result = {
        "overall_score": None,
        "silos": merged_silos,
        "official_rule_results": official_rule_results,
        "updated_silos": affected_silos
    }

    return result