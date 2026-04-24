from typing import Dict, Any, List


# =============================
# HELPERS
# =============================
def add(insights, msg): insights.append(msg)
def risk(risks, level, msg): risks.append({"level": level, "message": msg})
def rec(recs, msg): recs.append(msg)


# =============================
# CS.1 — STRATEGY ↔ HR
# =============================
def cs1(data, s1, s2, insights, recs, risks):
    if data.q10_written_strategy == "Yes" and data.q9_employee_understanding == "No":
        add(insights, "Strategy exists but is not understood by employees")
        rec(recs, "Run strategy cascade workshops")

    if data.q12_owner_dependency == "Yes" and data.q7_knowledge_concentration > 50:
        risk(risks, "CRITICAL", "Catastrophic succession risk")
        rec(recs, "Immediate succession + knowledge transfer plan")


# =============================
# CS.2 — STRATEGY ↔ EFFICIENCY
# =============================
def cs2(data, s1, s3, insights, recs):
    if data.q10_written_strategy == "Yes" and data.q2_sops in ["None", "Some"]:
        add(insights, "Strategy exists but not operationalized")
        rec(recs, "Translate strategy into SOPs")

    if data.q7_admin_percent > 60 and data.q4_automation == "No":
        rec(recs, "High ROI automation opportunity")


# =============================
# CS.3 — STRATEGY ↔ FINANCE
# =============================
def cs3(data, s4, s7, insights, recs, risks):
    if data.q6_growth_confidence >= 4 and data.q5_runway < 6:
        risk(risks, "HIGH", "Growth ambition exceeds financial runway")
        rec(recs, "Secure capital before expansion")

    if data.q1_customer_concentration >= 50:
        rec(recs, "Diversify customers before expansion")


# =============================
# CS.4 — HR → SERVICE CASCADE
# =============================
def cs4(data, s2, s3, s6, insights, recs, risks):
    if data.q5_turnover >= 50:
        add(insights, "Turnover damaging service quality")
        rec(recs, "Fix retention before scaling")

    if data.q3_roles_clear == "No" and data.q2_sops == "None":
        risk(risks, "CRITICAL", "Double blind spot: no roles + no processes")
        rec(recs, "Define roles AND SOPs immediately")


# =============================
# CS.5 — KNOWLEDGE RISK
# =============================
def cs5(data, s2, s6, insights, recs, risks):
    if data.q7_knowledge_concentration >= 25 and data.q5_turnover >= 25:
        risk(risks, "HIGH", "Knowledge loss imminent")
        rec(recs, "Run knowledge capture sprint")

    if data.q7_knowledge_concentration > 50 and s6.get("servqual", {}).get("score", 0) >= 80:
        add(insights, "Service quality depends on one person")


# =============================
# CS.6 — WASTE LOOP
# =============================
def cs6(data, s1, s2, s3, s4, insights, recs):
    waste = 0

    if data.q2_sops == "None": waste += 10
    if data.q8_duplication == "A lot": waste += 12
    if data.q8b_severity == "Critical": waste += 8
    if data.q5_turnover >= 50: waste += 15
    if data.q4_automation == "No" and data.q7_admin_percent > 50: waste += 10

    if waste >= 25:
        add(insights, f"High operational waste: {waste}%")
        rec(recs, "Launch operational excellence program")


# =============================
# CS.7 — MARKETING ↔ SERVICE
# =============================
def cs7(data, s5, s6, insights, recs):
    if s5.get("acquisition", {}).get("score", 0) >= 70 and data.q1_repeat_customers < 50:
        add(insights, "Leaky bucket: acquiring but not retaining")
        rec(recs, "Shift budget to retention")

    if data.q3_referral >= 4 and s5.get("lead_balance") != "INBOUND_DOMINANT":
        rec(recs, "Formalize referral program")


# =============================
# CS.8 — SERVICE → FINANCE
# =============================
def cs8(data, s4, s6, insights, recs, risks):
    if data.q1_repeat_customers >= 75:
        add(insights, "Strong retention supports stable revenue")

    if data.q2_quality <= 2 and data.q1_customer_concentration >= 50:
        risk(risks, "CRITICAL", "Poor quality + concentrated revenue")
        rec(recs, "Fix service quality immediately")


# =============================
# CS.9 — DIGITAL → STRATEGY
# =============================
def cs9(s1, s3, insights):
    quadrant = s3.get("quadrant", {}).get("name")

    if quadrant == "Digirati":
        add(insights, "Digital maturity creates competitive moat")

    if quadrant == "Beginners":
        add(insights, "Digital weakness is a competitive risk")


# =============================
# CS.10 — RISK → STRATEGY
# =============================
def cs10(s7, insights, recs):
    if s7.get("enterprise_risk", {}).get("score", 100) < 50:
        rec(recs, "Prioritize enterprise risk mitigation")


# =============================
# CS.12 — AARRR FULL
# =============================
def cs12(s4, s5, s6, insights, recs):
    acquisition = s5.get("acquisition", {}).get("score", 0)
    retention = s6.get("repeat_score", 0)
    revenue = s5.get("revenue_score", 0)

    weakest = min(
        [("Acquisition", acquisition), ("Retention", retention), ("Revenue", revenue)],
        key=lambda x: x[1]
    )

    rec(recs, f"Focus on weakest funnel stage: {weakest[0]}")


# =============================
# CS.14 — CLV:CAC
# =============================
def cs14(s6, s5, insights, recs, risks):
    clv = s6.get("clv", {}).get("score", 1)
    cac = 1

    ratio = clv / cac

    if ratio < 1:
        risk(risks, "CRITICAL", "Unsustainable unit economics")
    elif ratio < 3:
        rec(recs, "Improve acquisition efficiency")


# =============================
# CS.16 — DIGITAL ROI
# =============================
def cs16(s3, s4, insights, recs):
    quadrant = s3.get("quadrant", {}).get("name")

    if quadrant in ["Beginners", "Conservatives"] and s4.get("waste_percent", 0) >= 25:
        rec(recs, "Digital transformation ROI is high")


# =============================
# PRIORITIES ENGINE
# =============================
def priorities(insights, risks):
    priority = [r["message"] for r in risks if r["level"] == "CRITICAL"]
    return priority[:5]


# =============================
# ✅ MAIN FUNCTION (THIS FIXES YOUR ERROR)
# =============================
def run_cross_analysis(data, silo1, silo2, silo3, silo4, silo5, silo6, silo7):

    insights: List[str] = []
    recs: List[str] = []
    risks: List[Dict[str, str]] = []

    cs1(data, silo1, silo2, insights, recs, risks)
    cs2(data, silo1, silo3, insights, recs)
    cs3(data, silo4, silo7, insights, recs, risks)
    cs4(data, silo2, silo3, silo6, insights, recs, risks)
    cs5(data, silo2, silo6, insights, recs, risks)
    cs6(data, silo1, silo2, silo3, silo4, insights, recs)
    cs7(data, silo5, silo6, insights, recs)
    cs8(data, silo4, silo6, insights, recs, risks)
    cs9(silo1, silo3, insights)
    cs10(silo7, insights, recs)
    cs12(silo4, silo5, silo6, insights, recs)
    cs14(silo6, silo5, insights, recs, risks)
    cs16(silo3, silo4, insights, recs)

    return {
        "insights": insights,
        "recommendations": recs,
        "risks": risks,
        "top_priorities": priorities(insights, risks)
    }