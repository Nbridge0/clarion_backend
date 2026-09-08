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
# SILO-SPECIFIC QUESTION SCOPE
# =========================================================

SILO_QUESTION_IDS = {
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
        28, 29, 30, 38,
        43, 44, 45, 46, 47, 48
    }
}


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

    allowed_ids = SILO_QUESTION_IDS.get(
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
# INTELLIGENT SILO FINDINGS
# =========================================================
def build_intelligent_silo_findings(
    *,
    silo_name: str,
    answers: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Convert evidence-backed assessment results into
    meaningful user-facing findings.
    """

    semantic_answers = build_answer_evidence(
        answers,
        silo_name
    )

    evidence = {
        "silo": silo_name,
        "direct_assessment_evidence": semantic_answers
    }


    instructions = """
You are the analytical intelligence layer for PULSE.

You are analysing ONE business silo using ONLY direct answers
provided by the respondent.

The supplied evidence contains:

- question_id
- the meaning of the question
- the respondent's actual answer

Your job is to identify useful business findings while remaining
strictly faithful to those answers.

=========================================================
ABSOLUTE EVIDENCE RULES
=========================================================

1. Use ONLY direct_assessment_evidence.

2. Every factual statement in a finding must be directly supported
   by one or more supplied assessment answers.

3. Never invent or calculate a metric that was not directly asked
   in the assessment.

4. Never manufacture:
   - percentages
   - averages
   - financial ratios
   - scores
   - health scores
   - maturity scores
   - risk scores
   - benchmark scores
   - indexes
   - probabilities
   - financial values
   - customer values
   - employee values

5. Never create or infer formal metrics such as:
   - NPS
   - SERVQUAL
   - CLV
   - CAC
   - CLV:CAC
   - ROE
   - net profit margin
   - DSO
   - cash conversion cycle
   - asset turnover
   - digital intensity scores
   - transformation management scores
   - team health scores
   - positioning scores
   - segmentation scores
   unless that exact metric was explicitly measured in the
   assessment evidence.

=========================================================
INTERPRETATION RULES
=========================================================

6. You MAY make cautious qualitative interpretations where the
   relationship is directly supported by the answers.

For example:

If the respondent says:
- more than 50% of critical expertise is held by one person

you may say:
- there is substantial key-person concentration.

You may NOT invent a numerical risk score.

7. Do not convert an answer range into an exact value.

For example:

"25-50%" must remain "25-50%".

Do NOT convert it into:
37.5%.

8. Do not turn absence of a selected option into negative evidence.

For example:

If "speed" is not selected as something customers praise,
you may NOT conclude that response speed is poor.

9. Do not interpret:

"No suspected financial waste"

as proof that:
- cost management is healthy;
- financial controls are strong;
- no waste exists.

You may only state that:
- the respondent does not currently report suspected financial waste.

10. Do not label a result:
- healthy
- unhealthy
- strong
- weak
- excellent
- poor
- critical
- high risk
- low risk

unless that description follows plainly from the actual answer itself
or from an explicit assessment category supplied in the evidence.

Prefer factual wording such as:

- "less than 25% turnover was reported"
- "25-50% recurring revenue was reported"
- "some employees understand company goals"
- "SOPs exist for some processes"
- "sanctions screening has no formal process"

rather than inventing benchmark labels.

11. Do not claim causation unless the answers directly establish it.

Use cautious wording such as:

- may constrain
- creates exposure to
- may contribute to
- indicates a potential gap
- suggests an area to investigate

where causation has not been measured.

12. Do not claim that one answer caused another answer.

13. Do not exaggerate.

14. Do not minimise genuine risks shown directly by the answers.

=========================================================
MULTI-ANSWER ANALYSIS
=========================================================

15. You should connect multiple answers when their relationship is
    logically relevant.

Example:

A written strategy together with only partial employee understanding
can support a finding that internal strategic alignment may be incomplete.

16. When connecting answers, explicitly state which evidence supports
    the conclusion.

17. Do not combine unrelated answers merely to create more findings.

=========================================================
FINDINGS
=========================================================

18. Do not force a fixed number of findings.

19. Findings should represent meaningful conclusions, not repetitions
    of every answer.

20. Do not create a positive finding simply because an answer does
    not reveal a problem.

21. Do not create a negative finding simply because a positive option
    was not selected.

22. Recommendations must directly address the evidence described in
    the finding.

23. Recommendations may suggest reasonable next actions, but must not
    assume facts about the company that were not supplied.

24. Use professional British English.

=========================================================
EVIDENCE TRACEABILITY
=========================================================

25. Every finding MUST contain evidence_question_ids.

26. evidence_question_ids may contain ONLY question IDs actually
    supplied in direct_assessment_evidence.

27. Include every question materially used to reach the finding.

Return ONLY valid JSON in exactly this structure:

{
  "findings": [
    {
      "title": "short factual business conclusion",
      "analysis": "clear explanation based only on supplied answers",
      "evidence_question_ids": [1, 2],
      "recommendations": [
        "specific evidence-grounded action"
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

        if raw.startswith(
            "```"
        ):
            raw = (
                raw
                .strip("`")
                .strip()
            )

            if raw.lower().startswith(
                "json"
            ):
                raw = raw[
                    4:
                ].strip()

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

        clean_findings = []

        for finding in findings:

            if not isinstance(
                finding,
                dict
            ):
                continue

            title = str(
                finding.get(
                    "title"
                )
                or ""
            ).strip()

            analysis = str(
                finding.get(
                    "analysis"
                )
                or ""
            ).strip()

            evidence_question_ids = finding.get(
                "evidence_question_ids"
            ) or []

            if not isinstance(
                evidence_question_ids,
                list
            ):
                evidence_question_ids = []

            valid_question_ids = {
                int(item["question_id"])
                for item in semantic_answers
                if str(
                    item.get("question_id")
                ).isdigit()
            }

            clean_evidence_question_ids = []

            for question_id in evidence_question_ids:

                try:
                    question_id = int(
                        question_id
                   )
                except Exception:
                    continue

                if question_id not in valid_question_ids:
                    continue

                if question_id not in clean_evidence_question_ids:
                    clean_evidence_question_ids.append(
                        question_id
                    )

            recommendations = finding.get(
                "recommendations"
            ) or []

            if not isinstance(
                recommendations,
                list
            ):
                recommendations = [
                    recommendations
                ]

            recommendations = [
                str(item).strip()
                for item in recommendations
                if str(
                    item
                    or ""
                ).strip()
            ]

            if (
                not title
                or not analysis
                or not clean_evidence_question_ids
            ):
                continue

            clean_findings.append({
                "title": title,
                "analysis": analysis,
                "evidence_question_ids": clean_evidence_question_ids,
                "recommendations": recommendations
            })

        return {
            "findings": clean_findings
        }


    except Exception as error:

        print(
            "OPENAI SILO ANALYSIS ERROR:",
            {
                "silo": silo_name,
                "error_type": (
                    type(error).__name__
                ),
                "error": str(error)
            }
        )

        return {
            "findings": []
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


    # =====================================================
    # 1. GENERATE USER-FACING SILO ANALYSIS IN PARALLEL
    # =====================================================
    #
    # IMPORTANT:
    #
    # The user-facing intelligence layer receives ONLY:
    #
    # - exact assessment question meaning;
    # - exact respondent answer.
    #
    # It does NOT receive synthetic silo scores,
    # framework calculations or legacy cross-rules.
    #
    # =====================================================

    silo_names = list(
        SILO_QUESTION_IDS.keys()
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
                answers=data
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

                if not isinstance(
                    silo_result,
                    dict
                ):
                    silo_result = {
                        "findings": []
                    }

                intelligent_silos[
                    silo_name
                ] = silo_result

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


    # =====================================================
    # 2. DO NOT MANUFACTURE AN OVERALL SCORE
    # =====================================================

    result = {
        "overall_score": None,
        "silos": intelligent_silos
    }


    # =====================================================
    # 3. OPTIONAL LEGACY DEBUG ANALYSIS
    # =====================================================
    #
    # These deterministic calculations are deliberately
    # isolated from the normal PULSE response.
    #
    # They are executed ONLY when:
    #
    # PULSE_INCLUDE_RAW_ANALYSIS=true
    #
    # This means an outdated rule can never break the
    # customer-facing analysis during normal use.
    #
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