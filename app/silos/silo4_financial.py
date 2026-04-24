from typing import Dict, Any


# =============================
# RULE 4.1 — REVENUE CONCENTRATION
# =============================
def revenue_concentration(data):
    pct = data.get("q1_customer_concentration", 0)

    if pct > 75:
        return {"risk": "CRITICAL", "score": 10}
    elif pct >= 50:
        return {"risk": "HIGH", "score": 30}
    elif pct >= 25:
        return {"risk": "MODERATE", "score": 50}
    elif pct >= 15:
        return {"risk": "LOW", "score": 80}
    else:
        return {"risk": "LOW", "score": 100}


# =============================
# RULE 4.3 — BUSINESS MODEL
# =============================
def business_model(data):
    recurring = data.get("q3_recurring_revenue", 0)

    if recurring >= 75:
        return {"type": "SUBSCRIPTION", "predictability": "HIGH"}
    elif recurring >= 25:
        return {"type": "HYBRID", "predictability": "MEDIUM"}
    else:
        return {"type": "PROJECT", "predictability": "LOW"}


# =============================
# RULE 4.4 — CASH CONVERSION CYCLE
# =============================
def cash_conversion_cycle(data):
    model = business_model(data)["type"]

    DIO = 0

    if model == "SUBSCRIPTION":
        DSO = 15
    elif model == "HYBRID":
        DSO = 45
    else:
        DSO = 60

    if data.get("q2_suspects_waste") == "Yes":
        DSO += 20

    DPO = 30

    ccc = DIO + DSO - DPO

    return {
        "ccc_days": ccc,
        "DSO": DSO
    }


# =============================
# RULE 4.5 — WORKING CAPITAL
# =============================
def working_capital_efficiency(ccc):
    if ccc <= 20:
        return "EXCELLENT"
    elif ccc <= 40:
        return "GOOD"
    elif ccc <= 60:
        return "POOR"
    else:
        return "CRITICAL"


# =============================
# RULE 4.6 — NET PROFIT MARGIN
# =============================
def net_profit_margin(data, silo1=None, silo3=None):
    npm = 15.0

    if data.get("q2_suspects_waste") == "Yes":
        npm *= 0.85

    if silo1 and silo1.get("staff_alignment", {}).get("score", 0) < 50:
        npm *= 0.90

    if silo3 and silo3.get("sop_impact"):
        npm *= 0.92

    return npm


# =============================
# RULE 4.7 — ASSET TURNOVER
# =============================
def asset_turnover(data, silo2=None, silo3=None):
    at = 2.0

    if data.get("q1_employee_count", 0) > 50:
        at *= 0.9

    if silo3 and silo3.get("digital_intensity", {}).get("score", 0) >= 70:
        at *= 1.1

    return at


# =============================
# RULE 4.8 — ROE
# =============================
def return_on_equity(npm, at):
    leverage = 1.5
    roe = npm * at * leverage

    if npm > 15:
        driver = "MARGIN"
    elif at > 2:
        driver = "EFFICIENCY"
    elif leverage > 1.8:
        driver = "LEVERAGE"
    else:
        driver = "BALANCED"

    return {
        "roe": roe,
        "driver": driver
    }


# =============================
# RULE 4.9 — WASTE VALUE
# =============================
def waste_value(data, silo1=None, silo2=None, silo3=None):
    waste_pct = 0

    if data.get("q2_suspects_waste") == "Yes":
        waste_pct += 10

    if silo3 and silo3.get("bottleneck", {}).get("category"):
        waste_pct += 8

    # FIX: systems_efficiency is a number
    if silo1 and silo1.get("systems_efficiency") == 50:
        waste_pct += 12

    if silo3 and data.get("q2_sops") == "None":
        waste_pct += 10

    if silo2 and data.get("q5_turnover", 0) >= 50:
        waste_pct += 15

    return waste_pct


# =============================
# RULE 4.10 — FINANCIAL HEALTH
# =============================
def financial_health(data, concentration_score, ccc, silo6=None):
    repeat_score = silo6.get("repeat_score", 50) if silo6 else 50

    revenue_stability = (
        concentration_score * 0.4 +
        data.get("q3_recurring_revenue", 0) * 0.35 +
        repeat_score * 0.25
    )

    ccc_score = {
        "EXCELLENT": 100,
        "GOOD": 75,
        "POOR": 50,
        "CRITICAL": 25
    }

    cash_eff = ccc_score[working_capital_efficiency(ccc)]

    if revenue_stability < 40 or cash_eff < 40:
        risk = "HIGH"
    elif revenue_stability < 60:
        risk = "MEDIUM"
    else:
        risk = "LOW"

    return {
        "revenue_stability": revenue_stability,
        "cash_efficiency": cash_eff,
        "risk_level": risk
    }


# =============================
# RULE 4.11 — CCC + RUNWAY
# =============================
def cash_flow_crisis(ccc, silo7=None):
    if silo7:
        runway = silo7.get("runway_months", 12)

        if ccc > 45 and runway < 3:
            return {
                "alert": "Critical cash flow crisis imminent",
                "priority": "IMMEDIATE"
            }

    return None


# =============================
# MAIN
# =============================
def run_silo4(data, silo1=None, silo2=None, silo3=None, silo6=None, silo7=None):

    concentration = revenue_concentration(data)
    model = business_model(data)

    ccc_data = cash_conversion_cycle(data)
    ccc = ccc_data["ccc_days"]

    npm = net_profit_margin(data, silo1, silo3)
    at = asset_turnover(data, silo2, silo3)
    roe = return_on_equity(npm, at)

    waste_pct = waste_value(data, silo1, silo2, silo3)

    health = financial_health(data, concentration["score"], ccc, silo6)

    return {
        "concentration": concentration,
        "business_model": model,
        "ccc": ccc_data,
        "working_capital": working_capital_efficiency(ccc),
        "net_profit_margin": npm,
        "asset_turnover": at,
        "roe": roe,
        "waste_percent": waste_pct,
        "financial_health": health,
        "cash_flow_risk": cash_flow_crisis(ccc, silo7)
    }