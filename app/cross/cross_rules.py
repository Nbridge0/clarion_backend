from app.types.results import Insight, RiskItem


def run_cross_rules(twin):

    s1 = twin.silos.get("strategy", {})
    s2 = twin.silos.get("hr", {})
    s3 = twin.silos.get("efficiency", {})
    s4 = twin.silos.get("financial", {})
    s5 = twin.silos.get("marketing", {})
    s6 = twin.silos.get("service", {})
    s7 = twin.silos.get("risk", {})

    # =========================================================
    # CS.1 — STRATEGY ↔ HR
    # =========================================================
    if s1.get("strategy_clarity_label") == "HIGH" and s2.get("commitment", 100) < 40:
        twin.insights.append(Insight(
            "Strategy exists but not communicated — alignment failure",
            "CS.1",
            "CRITICAL"
        ))

    if s1.get("staff_alignment", 100) < 40 and s2.get("knowledge_concentration", 0) > 50:
        twin.insights.append(Insight(
            "Catastrophic succession risk — owner + knowledge concentration",
            "CS.1",
            "CRITICAL"
        ))

    # =========================================================
    # CS.2 — STRATEGY ↔ EFFICIENCY
    # =========================================================
    if s1.get("strategy_clarity", 0) >= 70 and s3.get("digital_quadrant") == "BEGINNERS":
        twin.insights.append(Insight(
            "Strategy not operationalized into processes",
            "CS.2",
            "HIGH"
        ))

    if s1.get("staff_alignment", 100) < 40 and s3.get("digital_intensity", 0) < 40:
        twin.insights.append(Insight(
            "High admin burden + no automation — major efficiency loss",
            "CS.2",
            "HIGH"
        ))

    # =========================================================
    # CS.3 — STRATEGY ↔ FINANCIAL
    # =========================================================
    if s1.get("strategy_clarity", 0) >= 70 and s7.get("resilience") in ["WEAK", "CRITICAL"]:
        twin.insights.append(Insight(
            "Growth ambition exceeds financial capacity",
            "CS.3",
            "CRITICAL"
        ))

    if s4.get("concentration_score", 100) < 50 and len(s1.get("opportunities", [])) > 0:
        twin.insights.append(Insight(
            "Expansion while dependent on few clients increases risk",
            "CS.3",
            "HIGH"
        ))

    # =========================================================
    # CS.4 — HR → SERVICE CASCADE
    # =========================================================
    if s2.get("turnover", 0) >= 50:
        twin.insights.append(Insight(
            "Turnover is degrading service quality and operations",
            "CS.4",
            "CRITICAL"
        ))

    if s2.get("role_clarity") == "No" and s3.get("transformation_management", 100) < 40:
        twin.insights.append(Insight(
            "Double blind spot — no roles + no processes",
            "CS.4",
            "CRITICAL"
        ))

    # =========================================================
    # CS.5 — KNOWLEDGE RISK
    # =========================================================
    if s2.get("knowledge_concentration", 0) >= 25 and s2.get("turnover", 0) >= 25:
        twin.risks.append(RiskItem(
            "Knowledge loss risk",
            "Likely",
            "Major",
            "HIGH",
            "CS.5",
            "Operational"
        ))

    if s2.get("knowledge_concentration", 0) > 50 and s6.get("service_quality", 0) >= 80:
        twin.insights.append(Insight(
            "Service depends on one person — high fragility",
            "CS.5",
            "CRITICAL"
        ))

    # =========================================================
    # CS.6 — WASTE LOOP
    # =========================================================
    waste = 0

    if s3.get("transformation_management", 100) < 40:
        waste += 10
    if s1.get("systems_efficiency", 100) < 50:
        waste += 12
    if s3.get("bottleneck_severity") == "Critical impact":
        waste += 8
    if s2.get("turnover", 0) >= 50:
        waste += 15

    if waste >= 25:
        twin.insights.append(Insight(
            f"High operational waste detected (~{waste}%)",
            "CS.6",
            "HIGH"
        ))

    # =========================================================
    # CS.7 — MARKETING ↔ SERVICE
    # =========================================================
    if s5.get("acquisition_score", 0) >= 70 and s6.get("retention") in ["FAIR", "POOR"]:
        twin.insights.append(Insight(
            "Leaky bucket — strong acquisition but weak retention",
            "CS.7",
            "CRITICAL"
        ))

    if s6.get("nps", 0) > 50 and s5.get("lead_balance") == "OUTBOUND":
        twin.insights.append(Insight(
            "Referral opportunity not captured — build referral system",
            "CS.7",
            "HIGH"
        ))

    # =========================================================
    # CS.8 — SERVICE → FINANCIAL
    # =========================================================
    if s6.get("retention") == "EXCELLENT" and s4.get("business_model") != "PROJECT":
        twin.insights.append(Insight(
            "Strong retention driving predictable revenue",
            "CS.8",
            "MEDIUM"
        ))

    if s6.get("service_quality", 100) < 50 and s4.get("concentration_score", 100) < 50:
        twin.insights.append(Insight(
            "Poor service + concentration = critical business risk",
            "CS.8",
            "CRITICAL"
        ))

    # =========================================================
    # CS.9 — DIGITAL ↔ COMPETITIVE POSITION
    # =========================================================
    if s3.get("digital_quadrant") == "DIGIRATI" and s1.get("shared_values_strength") != "STRONG":
        twin.swot["strengths"].append("Digital superiority")

    if s3.get("digital_quadrant") == "BEGINNERS":
        twin.swot["threats"].append("Digital disruption risk")

    # =========================================================
    # CS.10 — RISK → STRATEGY
    # =========================================================
    if s7.get("enterprise_risk_score", 100) < 50:
        twin.insights.append(Insight(
            "Risk level too high — focus must shift to stabilization",
            "CS.10",
            "CRITICAL"
        ))

    # =========================================================
    # CS.11 — COMPLIANCE ↔ FINANCIAL
    # =========================================================
    if s7.get("compliance_maturity") in ["BASIC", "NON-EXISTENT"] and s4.get("concentration_score", 100) < 50:
        twin.insights.append(Insight(
            "Compliance failure could be existential",
            "CS.11",
            "CRITICAL"
        ))

    # =========================================================
    # CS.12 — FULL AARRR
    # =========================================================
    funnel = [
        s5.get("acquisition_score", 0),
        s6.get("service_quality", 0),
        50,
        (s6.get("nps", 0) / 100) * 100,
        s5.get("revenue_score", 0)
    ]

    weakest = min(funnel)

    if weakest < 40:
        twin.insights.append(Insight(
            "Critical funnel weakness detected",
            "CS.12",
            "CRITICAL"
        ))

    # =========================================================
    # CS.13 — WASTE TYPES
    # =========================================================
    if s3.get("bottleneck") == "PROCESS":
        twin.insights.append(Insight(
            "Waiting waste at bottlenecks",
            "CS.13",
            "MEDIUM"
        ))

    if s6.get("service_quality", 100) < 50:
        twin.insights.append(Insight(
            "Defects waste from poor service quality",
            "CS.13",
            "HIGH"
        ))

    # =========================================================
    # CS.14 — CLV:CAC
    # =========================================================
    clv = s6.get("clv", 1)
    cac = 1  # proxy

    ratio = clv / cac

    if ratio < 1:
        twin.insights.append(Insight(
            "Unsustainable unit economics — losing money per customer",
            "CS.14",
            "CRITICAL"
        ))

    # =========================================================
    # CS.15 — TURNOVER COST
    # =========================================================
    if s2.get("turnover", 0) > 50:
        twin.insights.append(Insight(
            "Turnover cost significantly impacting revenue",
            "CS.15",
            "HIGH"
        ))

    # =========================================================
    # CS.16 — DIGITAL ROI
    # =========================================================
    if s3.get("digital_quadrant") in ["BEGINNERS", "CONSERVATIVES"] and waste >= 25:
        twin.insights.append(Insight(
            "Digital transformation ROI is high",
            "CS.16",
            "HIGH"
        ))

    # =========================================================
    # CS.17 — PRIORITIES (SIMPLIFIED OUTPUT)
    # =========================================================
    # (Full prioritization engine would rank all insights)

    # =========================================================
    # CS.18 — MARKETING → FINANCIAL
    # =========================================================
    if s5.get("stp_alignment", 100) < 60 and s4.get("concentration_score", 100) < 50:
        twin.insights.append(Insight(
            "Unfocused marketing causing customer dependency",
            "CS.18",
            "HIGH"
        ))

    # =========================================================
    # CS.19 — RISK → SERVICE
    # =========================================================
    if s7.get("compliance_maturity") in ["BASIC", "NON-EXISTENT"] and s6.get("retention") == "EXCELLENT":
        twin.insights.append(Insight(
            "Compliance risk threatens customer loyalty",
            "CS.19",
            "HIGH"
        ))

    # =========================================================
    # CS.20 — EFFICIENCY → MARKETING
    # =========================================================
    if s3.get("bottleneck_severity") == "Critical impact" and s5.get("acquisition_score", 0) >= 70:
        twin.insights.append(Insight(
            "Marketing generating demand operations cannot deliver",
            "CS.20",
            "CRITICAL"
        ))

    # =========================================================
    # CS.21 — FINANCE → RISK
    # =========================================================
    if s7.get("resilience") in ["WEAK", "CRITICAL"]:
        twin.insights.append(Insight(
            "Weak finances forcing reactive risk management",
            "CS.21",
            "HIGH"
        ))

    # =========================================================
    # CS.22 — HR → GROWTH
    # =========================================================
    if s2.get("turnover", 0) >= 50 and len(s1.get("opportunities", [])) > 0:
        twin.insights.append(Insight(
            "Growth not supported by team stability",
            "CS.22",
            "CRITICAL"
        ))

    # =========================================================
    # CS.23 — SERVICE → REPUTATION
    # =========================================================
    if s6.get("service_quality", 100) < 50:
        twin.risks.append(RiskItem(
            "Reputational risk from poor service",
            "Likely",
            "Major",
            "HIGH",
            "CS.23",
            "Strategic"
        ))

    # =========================================================
    # CS.24 — STRATEGY → RISK
    # =========================================================
    if s1.get("strategy_clarity", 0) >= 80 and waste >= 25:
        twin.risks.append(RiskItem(
            "Scaling inefficiency risk",
            "Likely",
            "Major",
            "HIGH",
            "CS.24",
            "Strategic"
        ))

    # =========================================================
    # CS.25 — PRICING POWER
    # =========================================================
    if s6.get("clv_segment") in ["HIGH", "PREMIUM"] and s6.get("service_quality", 0) > 70:
        twin.insights.append(Insight(
            "Pricing power exists — consider increasing prices",
            "CS.25",
            "HIGH"
        ))

    # =========================================================
    # CS.26 — MATURITY STAGE
    # =========================================================
    emp = s2.get("employee_count", 0)

    if emp < 10:
        stage = "STARTUP"
    elif emp < 50:
        stage = "GROWTH"
    else:
        stage = "MATURE"

    twin.scores["business_stage"] = stage