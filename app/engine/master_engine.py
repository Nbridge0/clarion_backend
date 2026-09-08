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
        # Direct Strategy evidence
        1, 2, 3, 4, 5, 6, 7,
        8, 9, 10, 11, 12, 13,

        # Rule 3.9 — SOP coverage affects Strategy systems
        21,

        # CS.22 — team capacity can constrain growth strategy
        14, 18
    },

    "people": {
        # Direct People evidence
        10,
        14, 15, 16, 17, 18, 19, 20,

        # Rule 3.9 — SOP coverage caps accountability
        21
    },

    "operations": {
        # Direct Operations evidence
        4, 5, 8, 9, 10, 11,
        21, 22, 23, 24, 25, 26, 27, 29
    },

    "financial": {
        # Direct Financial evidence
        28, 29, 30, 48
    },

    "marketing": {
        # Direct Marketing evidence
        2,
        31, 32, 33, 34, 35, 36, 37, 38,

        # CS.22 — team-capacity / sales-scalability rules
        12, 14, 18, 20
    },

    "service": {
        # Direct Service evidence
        20,
        38, 39, 40, 41, 42,

        # Rule 3.9 — SOP coverage affects service consistency
        21
    },

    "risk": {
        # Direct Risk evidence
        13, 18, 20, 27,
        28, 29, 30, 38, 40,
        43, 44, 45, 46, 47, 48
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
    # OPERATIONS — VENDOR RISK
    # Current Q27
    # =====================================================

    vendor_backup = answer_lower(
        answers,
        27
    )

    if "for some" in vendor_backup:
        results["operations"].append(
            make_rule_result(
                rule_id="3.6",
                silo="operations",
                title="Vendor concentration risk is medium",
                analysis=(
                    "Pre-vetted Tier-2 alternatives exist for only "
                    "some suppliers or services."
                ),
                evidence_question_ids=[
                    27
                ],
                recommendations=[
                    "Audit which critical vendors or services still lack pre-vetted alternatives."
                ],
                classification="MEDIUM"
            )
        )

    elif vendor_backup == "no":
        results["operations"].append(
            make_rule_result(
                rule_id="3.6",
                silo="operations",
                title="Vendor concentration risk is high",
                analysis=(
                    "No pre-vetted Tier-2 alternatives are available."
                ),
                evidence_question_ids=[
                    27
                ],
                recommendations=[
                    "Develop Tier-2 vendor relationships immediately."
                ],
                classification="HIGH"
            )
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
        or "some" in sop_coverage
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
    # FINANCIAL — RULE 4.1 REVENUE CONCENTRATION
    # Current Q28
    # =====================================================

    concentration_revenue = answer_lower(
        answers,
        28
    )

    if (
        "<5" in concentration_revenue
        or "under 5" in concentration_revenue
    ):
        results["financial"].append(
            make_rule_result(
                rule_id="4.1",
                silo="financial",
                title="Customer revenue concentration risk is low",
                analysis=(
                    "The largest customer represents less than 5% "
                    "of revenue, placing customer concentration in "
                    "the low-risk range."
                ),
                evidence_question_ids=[
                    28
                ],
                recommendations=[
                    "Maintain a diversified customer base."
                ],
                classification="LOW"
            )
        )


    # =====================================================
    # FINANCIAL — RULE 4.3 BUSINESS MODEL
    # Current Q30
    # =====================================================

    recurring = answer_lower(
        answers,
        30
    )

    if (
        "<25" in recurring
        or "under 25" in recurring
    ):
        results["financial"].append(
            make_rule_result(
                rule_id="4.3",
                silo="financial",
                title="Business model is project-based with low revenue predictability",
                analysis=(
                    "Less than 25% of revenue is recurring. Under "
                    "the official PULSE rule this is classified as "
                    "a project-based model with LOW revenue predictability."
                ),
                evidence_question_ids=[
                    30
                ],
                recommendations=[
                    "Develop recurring revenue streams to improve cash-flow predictability."
                ],
                classification="LOW"
            )
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
    # RISK — RULE 7.1 CONTRACTOR INSURANCE
    # Current Q43 + Q46
    # =====================================================

    contractor_insurance = answer_lower(
        answers,
        43
    )

    pi_cover = answer_lower(
        answers,
        46
    )

    if "sometimes" in contractor_insurance:
        results["risk"].append(
            make_rule_result(
                rule_id="7.1-CONTRACTOR-INSURANCE",
                silo="risk",
                title="Contractor insurance verification is a weak prevention barrier",
                analysis=(
                    "Subcontractor proof of insurance is required "
                    "only sometimes. The official Bowtie rule "
                    "classifies this as a WEAK prevention barrier."
                ),
                evidence_question_ids=[
                    43
                ],
                recommendations=[
                    "Require consistent proof of insurance from subcontractors."
                ],
                classification="WEAK"
            )
        )

    if "partial" in pi_cover:
        results["risk"].append(
            make_rule_result(
                rule_id="7.1-PI-COVER",
                silo="risk",
                title="Professional Indemnity coverage is a moderate recovery barrier",
                analysis=(
                    "Professional Indemnity insurance only partially "
                    "covers the largest contract. The official rule "
                    "classifies this recovery barrier as MODERATE."
                ),
                evidence_question_ids=[
                    46
                ],
                recommendations=[
                    "Review Professional Indemnity limits against the value of the largest contract."
                ],
                classification="MODERATE"
            )
        )


    # =====================================================
    # RISK — RULE 7.2 SANCTIONS
    # Current Q44
    # =====================================================

    sanctions = answer_lower(
        answers,
        44
    )

    if "no formal process" in sanctions:
        results["risk"].append(
            make_rule_result(
                rule_id="7.2",
                silo="risk",
                title="Sanctions screening control is absent and exposure is critical",
                analysis=(
                    "Sanctions screening has no formal process. "
                    "Under the official Bowtie rule this is an "
                    "ABSENT prevention barrier and triggers a "
                    "CRITICAL sanctions compliance gap."
                ),
                evidence_question_ids=[
                    44
                ],
                recommendations=[
                    "Implement a formal sanctions-screening process immediately."
                ],
                classification="CRITICAL"
            )
        )


    # =====================================================
    # RISK — UBO CONTROL
    # Current Q45
    # =====================================================

    ubo = answer_lower(
        answers,
        45
    )

    if "only if required by bank" in ubo:
        results["risk"].append(
            make_rule_result(
                rule_id="7.2-UBO",
                silo="risk",
                title="UBO verification is a weak prevention barrier",
                analysis=(
                    "Ultimate beneficial ownership is verified only "
                    "when required by a bank. The official Bowtie "
                    "definition classifies this as a WEAK barrier."
                ),
                evidence_question_ids=[
                    45
                ],
                recommendations=[
                    "Introduce consistent UBO verification independent of bank requirements."
                ],
                classification="WEAK"
            )
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

    revenue_concentration_high = (
        "50-75" in concentration_revenue
        or "75-100" in concentration_revenue
        or ">50" in concentration_revenue
        or "over 50" in concentration_revenue
    )

    recurring_below_25 = (
        "<25" in recurring
        or "under 25" in recurring
        or "0-25" in recurring
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

    employee_count = answer_lower(
        answers,
        14
    )

    small_team = (
        "0-5" in employee_count
        or "6-10" in employee_count
    )

    growth_opportunities = answer_lower(
        answers,
        12
    ) 

    growth_opportunities_are_ambitious = False

    if (
        small_team
        and turnover_at_least_50
        and growth_opportunities_are_ambitious
    ):

        results["strategy"].append(
            make_rule_result(
                rule_id="CS.22",
                silo="strategy",
                title="Team instability may constrain the growth strategy",
                analysis=(
                    "The business has a small team, employee turnover "
                    "is at least 50%, and growth opportunities are "
                    "being pursued. The cross-silo rule identifies "
                    "team stability as a prerequisite for scaling."
                ),
                evidence_question_ids=[
                    12,
                    14,
                    18
                ],
                recommendations=[
                    "Stabilise employee retention before materially scaling growth activity."
                ],
                classification="HIGH PRIORITY",
                kind="rule",
                confidence="high"
            )
        )

        results["marketing"].append(
            make_rule_result(
                rule_id="CS.22",
                silo="marketing",
                title="Team instability may constrain marketing-led growth",
                analysis=(
                    "A small team combined with employee turnover of "
                    "at least 50% can constrain the organisation's "
                    "capacity to support additional customer acquisition."
                ),
                evidence_question_ids=[
                    12,
                    14,
                    18
                ],
                recommendations=[
                    "Stabilise team capacity before materially increasing acquisition activity."
                ],
                classification="HIGH PRIORITY",
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

14. You may add additional qualitative findings from direct evidence,
    but they must not contradict or weaken official rule results.

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