from app.types.results import Insight, RiskItem


def process_financial_silo(data, twin):
    """
    FULL IMPLEMENTATION:
    Rule 4.1 → 4.11
    """

    Q1 = data.get("customer_concentration", 0)  # % of revenue from top customer
    Q2 = data.get("suspects_waste", "No")  # Yes / No
    Q3 = data.get("recurring_revenue", 0)  # %
    revenue = data.get("revenue", 1000000)  # fallback default

    silo = {}

    # =========================================================
    # RULE 4.1 — REVENUE CONCENTRATION RISK
    # =========================================================
    if Q1 > 75:
        concentration_score = 10
        risk_level = "CRITICAL"

        twin.insights.append(Insight(
            "Customer concentration crisis",
            "Rule 4.1",
            "CRITICAL"
        ))

    elif Q1 >= 50:
        concentration_score = 30
        risk_level = "HIGH"

        twin.insights.append(Insight(
            "Urgent customer diversification required",
            "Rule 4.1",
            "HIGH"
        ))

    elif Q1 >= 25:
        concentration_score = 50
        risk_level = "MODERATE"

    elif Q1 >= 15:
        concentration_score = 80
        risk_level = "LOW"

    else:
        concentration_score = 100
        risk_level = "LOW"

    silo["concentration_score"] = concentration_score
    silo["concentration_risk"] = risk_level

    # =========================================================
    # RULE 4.2 — CROSS-SILO ALERTS
    # =========================================================
    if risk_level in ["HIGH", "CRITICAL"]:
        twin.insights.append(Insight(
            "Strategy must prioritize customer diversification",
            "Rule 4.2",
            "HIGH"
        ))

        twin.swot["threats"].append("Customer concentration vulnerability")
        twin.swot["opportunities"].append("Market expansion to reduce concentration")

    # =========================================================
    # RULE 4.3 — BUSINESS MODEL CLASSIFICATION
    # =========================================================
    if Q3 >= 75:
        model = "SUBSCRIPTION"
        predictability = "HIGH"

    elif Q3 >= 25:
        model = "HYBRID"
        predictability = "MEDIUM"

    else:
        model = "PROJECT"
        predictability = "LOW"

        twin.insights.append(Insight(
            "Revenue is unpredictable — develop recurring streams",
            "Rule 4.3",
            "HIGH"
        ))

    silo["business_model"] = model
    silo["revenue_predictability"] = predictability

    # =========================================================
    # RULE 4.4 — CASH CONVERSION CYCLE (CCC)
    # =========================================================
    DIO = 0  # service business

    if Q3 >= 75:
        DSO = 15
    elif Q3 >= 25:
        DSO = 45
    else:
        DSO = 60

    if Q2 == "Yes":
        DSO += 20

    DPO = 30

    CCC = DIO + DSO - DPO

    silo["ccc"] = CCC

    # =========================================================
    # RULE 4.5 — WORKING CAPITAL EFFICIENCY
    # =========================================================
    if CCC <= 20:
        wc_eff = "EXCELLENT"
        wc_score = 100

    elif CCC <= 40:
        wc_eff = "GOOD"
        wc_score = 75

    elif CCC <= 60:
        wc_eff = "POOR"
        wc_score = 50

    else:
        wc_eff = "CRITICAL"
        wc_score = 25

        twin.insights.append(Insight(
            "Cash flow risk detected — slow cash conversion",
            "Rule 4.5",
            "CRITICAL"
        ))

    silo["working_capital_efficiency"] = wc_eff

    # =========================================================
    # RULE 4.6 — NET PROFIT MARGIN (DuPont)
    # =========================================================
    npm = 15

    if Q2 == "Yes":
        npm *= 0.85

    if twin.silos.get("strategy", {}).get("staff_alignment", 100) < 50:
        npm *= 0.90

    if twin.silos.get("efficiency", {}).get("digital_quadrant") == "BEGINNERS":
        npm *= 0.92

    silo["net_profit_margin"] = npm

    # =========================================================
    # RULE 4.7 — ASSET TURNOVER
    # =========================================================
    turnover = 2.0

    if twin.silos.get("hr", {}).get("employee_count", 0) > 50:
        turnover *= 0.9

    if twin.silos.get("efficiency", {}).get("digital_intensity", 0) >= 70:
        turnover *= 1.1

    silo["asset_turnover"] = turnover

    # =========================================================
    # RULE 4.8 — ROE (DuPont)
    # =========================================================
    leverage = 1.5

    ROE = npm * turnover * leverage

    silo["roe"] = ROE

    if npm > 15:
        driver = "MARGIN"
    elif turnover > 2:
        driver = "EFFICIENCY"
    elif leverage > 1.8:
        driver = "LEVERAGE"
    else:
        driver = "BALANCED"

    silo["profit_driver"] = driver

    # =========================================================
    # RULE 4.9 — WASTE IMPACT ($)
    # =========================================================
    waste_pct = 0

    if Q2 == "Yes":
        waste_pct += 8

    if twin.silos.get("strategy", {}).get("systems_efficiency", 100) < 50:
        waste_pct += 12

    if twin.silos.get("efficiency", {}).get("sop_coverage") == "None":
        waste_pct += 10

    if twin.silos.get("strategy", {}).get("staff_alignment", 100) < 40:
        waste_pct += 7

    if twin.silos.get("hr", {}).get("turnover", 0) >= 50:
        waste_pct += 15

    waste_value = revenue * (waste_pct / 100)

    silo["waste_percentage"] = waste_pct
    silo["waste_value"] = waste_value

    if waste_pct > 0:
        twin.insights.append(Insight(
            f"Waste reduction opportunity ≈ ${int(waste_value * 0.6)}",
            "Rule 4.9",
            "HIGH"
        ))

    # =========================================================
    # RULE 4.10 — FINANCIAL HEALTH SCORE
    # =========================================================
    repeat_score = 50  # placeholder until silo 6

    revenue_stability = (
        (concentration_score * 0.4) +
        (Q3 * 0.35) +
        (repeat_score * 0.25)
    )

    cash_efficiency = wc_score

    if revenue_stability < 40 or cash_efficiency < 40:
        financial_risk = "HIGH"
    elif revenue_stability < 60:
        financial_risk = "MEDIUM"
    else:
        financial_risk = "LOW"

    silo["financial_risk"] = financial_risk

    # =========================================================
    # RULE 4.11 — CCC + RUNWAY
    # =========================================================
    runway = twin.silos.get("risk", {}).get("runway", 12)

    if CCC > 45 and runway < 3:
        twin.insights.append(Insight(
            "Critical cash flow crisis imminent",
            "Rule 4.11",
            "CRITICAL"
        ))

    # =========================================================
    # SAVE SILO
    # =========================================================
    twin.silos["financial"] = silo