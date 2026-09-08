# app/engine/master_engine.py

from typing import Dict, Any, List
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
    api_key=OPENAI_API_KEY
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
    answers: Dict[str, Any],
    silo_rules_output: Any,
    cross_analysis: Any
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

        "direct_assessment_evidence": (
            semantic_answers
        ),

        "derived_silo_indicators": (
            silo_rules_output
        ),

        "cross_silo_evidence": (
            cross_analysis
        )
    }


    instructions = """
You are the analytical intelligence layer for PULSE.

You are analysing ONE business silo.

Your job is to identify meaningful business findings from the
assessment evidence supplied to you.

EVIDENCE HIERARCHY:

1. direct_assessment_evidence is the primary factual source;
2. derived_silo_indicators are interpretations calculated from those answers;
3. cross_silo_evidence may strengthen or contextualise a finding when
   genuinely relevant.

CRITICAL RULES:

1. Use ONLY the supplied evidence.

2. Never invent:
   - facts;
   - percentages;
   - financial values;
   - customer values;
   - employee values;
   - metrics;
   - timelines;
   - causes;
   - events;
   - KPIs;
   - risks.

3. Never claim that an unmeasured metric exists.

Examples of metrics that must NOT be invented unless explicitly supplied
as valid evidence include:
   - NPS;
   - CLV;
   - CAC;
   - CLV:CAC;
   - SERVQUAL;
   - ROE;
   - net profit margin;
   - asset turnover;
   - DSO;
   - cash conversion cycle.

4. A derived indicator is a decision-support signal, not an independently
observed business fact.

5. Direct user answers take precedence over a derived interpretation
if there is any conflict.

6. Ignore:
   - null;
   - None;
   - empty strings;
   - empty arrays;
   - empty dictionaries;
   - UNKNOWN;
   - unavailable values.

7. Cross-silo evidence must not become the sole basis of an unrelated
silo finding.

8. Every finding for the current silo must have direct support from:
   - at least one direct assessment answer relevant to this silo; or
   - a valid derived indicator based on those direct answers.

9. Do not turn implementation keys, internal framework names or
calculation names into user-facing findings.

10. Finding titles must state the actual business conclusion.

11. Analysis must explicitly explain what evidence supports the finding.

12. Do not claim causation when the evidence only supports:
   - association;
   - exposure;
   - warning;
   - potential constraint;
   - risk signal.

13. Recommendations must address the identified evidence directly.

14. Recommendations must not introduce facts that were not supplied.

15. Do not force a fixed number of findings.

16. If there is insufficient evidence for a meaningful finding,
return an empty findings array.

17. Do not copy examples from these instructions.

18. Use clear professional British English.

Return ONLY valid JSON with exactly this structure:

{
  "findings": [
    {
      "title": "short, specific business conclusion",
      "analysis": "evidence-based explanation of why this conclusion is supported",
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
            ):
                continue

            clean_findings.append({
                "title": title,
                "analysis": analysis,
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
    Run deterministic evidence extraction first,
    cross-silo analysis second,
    then generate user-facing findings.
    """

    if not isinstance(
        data,
        dict
    ):
        data = {}


    # =====================================================
    # 1. RUN SILO RULES
    # =====================================================

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


    # =====================================================
    # 2. CROSS-SILO ANALYSIS
    # =====================================================

    cross = run_cross_analysis(
        data=data,
        silo1=raw_silo1,
        silo2=raw_silo2,
        silo3=raw_silo3,
        silo4=raw_silo4,
        silo5=raw_silo5,
        silo6=raw_silo6,
        silo7=raw_silo7
    )


    # =====================================================
    # 3. GENERATE USER-FACING INTELLIGENCE
    # =====================================================

    intelligent_silos = {}

    for (
        silo_name,
        silo_output
    ) in raw_silos.items():

        intelligent_silos[
            silo_name
        ] = build_intelligent_silo_findings(
            silo_name=silo_name,
            answers=data,
            silo_rules_output=silo_output,
            cross_analysis=cross
        )


    # =====================================================
    # 4. DO NOT MANUFACTURE AN OVERALL SCORE
    # =====================================================
    #
    # The current silo outputs contain heterogeneous
    # indicators:
    #
    # - positive health scores;
    # - risk scores;
    # - 1-5 ratings;
    # - percentage-range midpoints;
    # - categorical indicators.
    #
    # Averaging these values would not produce a defensible
    # overall business score.
    #
    # =====================================================

    overall_score = None


    # =====================================================
    # 5. FINAL USER-FACING RESULT
    # =====================================================

    result = {
        "overall_score": overall_score,
        "silos": intelligent_silos,
        "cross_analysis": cross
    }


    # =====================================================
    # OPTIONAL RAW DEBUG OUTPUT
    # =====================================================
    #
    # Raw deterministic values should normally NOT be sent
    # to the user-facing dashboard/PDF.
    #
    # Enable only for backend debugging:
    #
    # PULSE_INCLUDE_RAW_ANALYSIS=true
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
        result[
            "raw_silos"
        ] = raw_silos


    return result