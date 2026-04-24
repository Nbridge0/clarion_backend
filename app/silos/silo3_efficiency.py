from typing import Dict, Any, List


# =============================
# RULE 3.1 — DIGITAL INTENSITY
# =============================
def digital_intensity(data):
    tool_map = {
        "Yes": 100,
        "Some": 60,
        "Not enough": 40,
        "None": 0
    }

    tool_score = tool_map.get(data.q3_tools, 0)
    automation_score = 100 if data.q4_automation == "Yes" else 0
    ai_score = 100 if data.q5_ai == "Yes" else 0

    ai_breadth = len(data.q6_ai_areas or []) / 6 * 100
    readiness = (data.q7_digital_readiness or 0) * 10

    avg = (tool_score + automation_score + ai_score + ai_breadth + readiness) / 5

    return {
        "score": avg,
        "level": "HIGH" if avg >= 60 else "LOW"
    }


# =============================
# RULE 3.2 — TRANSFORMATION MGMT
# =============================
def transformation_management(data):
    sop_map = {
        "All": 100,
        "Most": 75,
        "Some": 40,
        "None": 0
    }

    sop_score = sop_map.get(data.q2_sops, 0)

    strategy_score = 100 if data.q10_written_strategy == "Yes" else 0
    alignment_score = 100 if data.q9_employee_understanding == "Yes" else 40

    avg = (sop_score + strategy_score + alignment_score) / 3

    return {
        "score": avg,
        "level": "STRONG" if avg >= 60 else "WEAK"
    }


# =============================
# RULE 3.3 — MIT QUADRANT
# =============================
def mit_quadrant(di, tm):
    if di >= 60 and tm >= 60:
        return "DIGIRATI"

    if di >= 60 and tm < 60:
        return "FASHIONISTAS"

    if di < 60 and tm >= 60:
        return "CONSERVATIVES"

    return "BEGINNERS"


# =============================
# RULE 3.4 — BOTTLENECK
# =============================
BOTTLENECK_MAP = {
    "Not enough staff/capacity": "PEOPLE",
    "Staff skill gaps/training needs": "PEOPLE",
    "Cash flow/working capital constraints": "FINANCIAL",
    "Inefficient processes/workflows": "PROCESS",
    "Lack of clear procedures/SOPs": "PROCESS",
    "Decision-making delays/approvals": "PROCESS",
    "Technology/system limitations": "TECHNOLOGY",
    "Supplier/vendor dependencies": "VENDOR",
    "Sales/lead generation challenges": "COMMERCIAL",
    "Quality control issues": "QUALITY",
}


def bottleneck(data):
    category = BOTTLENECK_MAP.get(data.q8_bottleneck, None)

    severity = data.q8b_severity

    return {
        "category": category,
        "severity": severity
    }


# =============================
# RULE 3.5 — WASTE %
# =============================
def waste_estimate(data):
    sop_base = {
        "None": 35,
        "Some": 25,
        "Most": 15,
        "All": 5
    }

    waste = sop_base.get(data.q2_sops, 25)

    if data.q8b_severity == "Critical impact":
        waste += 20

    if data.q8_duplication == "A lot":
        waste += 15

    if data.q4_automation == "No" and len(data.q6_ai_areas or []) > 2:
        waste += 10

    if data.q7_admin_percent > 50:
        waste += 15

    return min(waste, 60)


# =============================
# RULE 3.6 — VENDOR RISK
# =============================
def vendor_risk(data, bottleneck_category):
    if data.q8_vendor_backup == "No" and bottleneck_category == "VENDOR":
        return {
            "risk": "HIGH",
            "alert": "Vendor single point of failure"
        }

    if data.q8_vendor_backup == "Some":
        return {
            "risk": "MEDIUM"
        }

    return {"risk": "LOW"}


# =============================
# RULE 3.7 — AI PRIORITY
# =============================
def ai_priority(data, bottleneck_category):
    scores = {}

    for area in data.q6_ai_areas or []:
        score = 0

        if bottleneck_category == "COMMERCIAL" and area == "Sales":
            score += 40

        if bottleneck_category == "PROCESS" and area == "Operations":
            score += 40

        if bottleneck_category == "FINANCIAL" and area == "Finance":
            score += 40

        if "Better tools/technology" in data.q6_perf_improvements:
            score += 10

        if "Better processes/workflows" in data.q6_perf_improvements:
            if area in ["Operations", "Admin"]:
                score += 30

        if data.q7_admin_percent > 50 and area == "Admin":
            score += 20

        if data.q4_automation == "No":
            score += 10

        scores[area] = score

    sorted_areas = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    return sorted_areas


# =============================
# RULE 3.8 — READINESS GAP
# =============================
def readiness_gap(data):
    if data.q7_digital_readiness >= 7:
        if data.q3_tools in ["None", "Not enough"] or data.q4_automation == "No" or data.q2_sops in ["None"]:
            return {
                "warning": "Digital readiness perception gap",
                "adjusted_score": data.q7_digital_readiness * 0.6
            }

    return None


# =============================
# RULE 3.9 — SOP IMPACT
# =============================
def sop_impact(data):
    if data.q2_sops in ["None", "Some"]:
        return {
            "systems_cap": 40,
            "accountability_cap": 50,
            "service_risk": True
        }

    return None


# =============================
# RULE 3.10 — ROADMAP
# =============================
def transformation_roadmap(quadrant):
    if quadrant == "BEGINNERS":
        return [
            "Document processes",
            "Fix bottlenecks",
            "Start automation pilot"
        ]

    if quadrant == "FASHIONISTAS":
        return [
            "Audit tech ROI",
            "Standardize processes",
            "Align tech with strategy"
        ]

    if quadrant == "CONSERVATIVES":
        return [
            "Identify automation opportunities",
            "Pilot AI",
            "Scale automation"
        ]

    if quadrant == "DIGIRATI":
        return [
            "Optimize systems",
            "Advanced AI",
            "Build tech moat"
        ]


# =============================
# MAIN
# =============================
def run_silo3(data):
    di = digital_intensity(data)
    tm = transformation_management(data)

    quadrant = mit_quadrant(di["score"], tm["score"])

    bottleneck_data = bottleneck(data)

    return {
        "digital_intensity": di,
        "transformation_management": tm,
        "quadrant": quadrant,
        "bottleneck": bottleneck_data,
        "waste_percent": waste_estimate(data),
        "vendor_risk": vendor_risk(data, bottleneck_data["category"]),
        "ai_priorities": ai_priority(data, bottleneck_data["category"]),
        "readiness_gap": readiness_gap(data),
        "sop_impact": sop_impact(data),
        "roadmap": transformation_roadmap(quadrant)
    }