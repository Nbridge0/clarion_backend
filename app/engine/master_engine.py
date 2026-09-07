# app/engine/master_engine.py

from typing import Dict, Any
import os
import json

from openai import OpenAI

# ✅ IMPORT SILOS (MATCH YOUR FILE NAMES)
from app.silos.silo1_strategy import run_silo1
from app.silos.silo2_hr import run_silo2
from app.silos.silo3_efficiency import run_silo3
from app.silos.silo4_financial import run_silo4
from app.silos.silo5_marketing import run_silo5
from app.silos.silo6_service import run_silo6
from app.silos.silo7_risk import run_silo7

# ✅ CROSS RULES
from app.cross.cross_rules import run_cross_analysis


OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not OPENAI_API_KEY:
    raise RuntimeError(
        "OPENAI_API_KEY is missing from the backend environment."
    )

OPENAI_ANALYSIS_MODEL = os.getenv(
    "OPENAI_CHAT_MODEL",
    "gpt-4.1-mini"
)

openai_client = OpenAI(
    api_key=OPENAI_API_KEY
)

def build_intelligent_silo_findings(
    *,
    silo_name: str,
    answers: Any,
    silo_rules_output: Any,
    cross_analysis: Any
) -> Dict[str, Any]:
    """
    Convert deterministic silo/rule output into meaningful,
    evidence-grounded business findings.

    The rule engines remain the source of truth.
    OpenAI interprets them; it does not replace them.
    """

    evidence = {
        "silo": silo_name,
        "answers": answers,
        "silo_rules_output": silo_rules_output,
        "cross_analysis": cross_analysis,
    }

    instructions = """
You are the analytical intelligence layer for PULSE.

Your job is to convert the supplied assessment evidence and rule-engine
output into meaningful business findings for ONE silo.

CRITICAL RULES:

1. Use ONLY the supplied evidence.
2. Do not invent facts, percentages, causes, risks, strengths,
   weaknesses, people, financial values, timelines, KPIs or events.
3. The deterministic silo rules are evidence and must remain authoritative.
4. User answers are evidence and must remain authoritative.
5. Cross-silo analysis may be used only when it genuinely supports
   the current silo finding.
6. Ignore null values, empty strings, empty arrays, empty dictionaries,
   "None", unavailable placeholders, and framework sections with no evidence.
7. Do NOT turn internal framework names into findings merely because
   they exist in the JSON.

For example, keys representing analytical frameworks must NOT automatically
become findings. A framework should only contribute evidence from which a
real business conclusion can be derived.

8. A finding title must describe the ACTUAL conclusion found in the
   evidence, not the name of the calculation/framework that produced it.
9. Do not produce generic filler such as:
   - monitor this area
   - create an action plan
   - review this metric
   unless the evidence specifically supports that recommendation.
10. Recommendations must directly address the finding and must be
    realistically actionable from the supplied evidence.
11. Causal analysis must explain WHY the finding follows from the
    evidence. Do not state causation when the evidence only supports
    association or a warning signal.
12. Do not force a fixed number of findings.
    Return only meaningful findings supported by the evidence.
13. If the evidence does not support a meaningful finding, return an
    empty findings array.
14. Never copy examples from these instructions.
15. Do not expose raw implementation keys or internal framework names
    as the user-facing title unless that term itself is genuinely the
    business conclusion.

Return ONLY valid JSON with exactly this structure:

{
  "findings": [
    {
      "title": "short, specific business conclusion",
      "analysis": "clear causal/evidence-based explanation",
      "recommendations": [
        "specific evidence-grounded action",
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
            response.output_text or ""
        ).strip()

        if raw.startswith("```"):
            raw = raw.strip("`").strip()

            if raw.lower().startswith("json"):
                raw = raw[4:].strip()

        parsed = json.loads(raw)

        findings = parsed.get("findings")

        if not isinstance(findings, list):
            findings = []

        clean_findings = []

        for finding in findings:
            if not isinstance(finding, dict):
                continue

            title = str(
                finding.get("title") or ""
            ).strip()

            analysis = str(
                finding.get("analysis") or ""
            ).strip()

            recommendations = finding.get(
                "recommendations"
            ) or []

            if not isinstance(recommendations, list):
                recommendations = [
                    recommendations
                ]

            recommendations = [
                str(item).strip()
                for item in recommendations
                if str(item or "").strip()
            ]

            if not title or not analysis:
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
                "error_type": type(error).__name__,
                "error": str(error)
            }
        )

        # IMPORTANT:
        # Do not fabricate analysis if OpenAI fails.
        return {
            "findings": []
        }

# =========================
# 🧠 MASTER ENGINE
# =========================
def run_full_analysis(data: Any) -> Dict[str, Any]:
    """
    Runs all deterministic PULSE silo rules first,
    then uses OpenAI to convert the rule evidence into
    meaningful user-facing findings.
    """

    # =====================================================
    # 1. RUN ALL EXISTING SILO RULE ENGINES
    # =====================================================

    raw_silo1 = run_silo1(data)
    raw_silo2 = run_silo2(data)
    raw_silo3 = run_silo3(data)
    raw_silo4 = run_silo4(data)
    raw_silo5 = run_silo5(data)
    raw_silo6 = run_silo6(data)
    raw_silo7 = run_silo7(data)

    raw_silos = {
        "strategy": raw_silo1,
        "people": raw_silo2,
        "operations": raw_silo3,
        "financial": raw_silo4,
        "marketing": raw_silo5,
        "service": raw_silo6,
        "risk": raw_silo7,
    }


    # =====================================================
    # 2. RUN YOUR EXISTING CROSS-SILO RULES
    # =====================================================

    cross = run_cross_analysis(
        data=data,
        silo1=raw_silo1,
        silo2=raw_silo2,
        silo3=raw_silo3,
        silo4=raw_silo4,
        silo5=raw_silo5,
        silo6=raw_silo6,
        silo7=raw_silo7,
    )


    # =====================================================
    # 3. CALCULATE EXISTING NUMERIC SCORE
    # =====================================================

    scores = []

    for silo in raw_silos.values():

        if not isinstance(silo, dict):
            continue

        for value in silo.values():

            if (
                isinstance(value, dict)
                and isinstance(
                    value.get("score"),
                    (int, float)
                )
            ):
                scores.append(
                    value["score"]
                )

            elif isinstance(
                value,
                (int, float)
            ):
                scores.append(value)

    overall_score = (
        sum(scores) / len(scores)
        if scores
        else 0
    )


    # =====================================================
    # 4. OPENAI INTERPRETS EACH SILO'S REAL RULE OUTPUT
    # =====================================================

    intelligent_silos = {}

    for silo_name, silo_output in raw_silos.items():

        intelligent_silos[silo_name] = (
            build_intelligent_silo_findings(
                silo_name=silo_name,
                answers=data,
                silo_rules_output=silo_output,
                cross_analysis=cross
            )
        )


    # =====================================================
    # 5. FINAL OUTPUT
    # =====================================================

    return {
        "overall_score": round(
            overall_score,
            2
        ),

        # This is what your dashboard should display.
        "silos": intelligent_silos,

        # Keep raw deterministic results for traceability.
        "raw_silos": raw_silos,

        "cross_analysis": cross
    }