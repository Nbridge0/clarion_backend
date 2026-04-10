from app.types.results import Insight, RiskItem


def process_hr_silo(data, twin):
    """
    Implements ALL:
    Rule 2.1 → 2.10
    Lencioni 5 Dysfunctions
    Turnover + Knowledge + Structure logic
    """

    Q1 = data.get("employee_count", 0)
    Q2 = data.get("departments", 0)
    Q3 = data.get("role_clarity", "No")  # Yes / Some / No
    Q4 = data.get("engagement_measured", "No")  # Yes / No
    Q5 = data.get("turnover", 0)
    Q6 = data.get("performance_improvements", [])
    Q7 = data.get("knowledge_concentration", 0)

    silo = {}

    # =========================================================
    # RULE 2.1 — TRUST (FOUNDATION)
    # =========================================================
    trust = 0

    if Q4 == "Yes":
        trust += 30

    if Q5 < 25:
        trust += 40
    elif Q5 < 50:
        trust += 20

    if Q3 == "Yes":
        trust += 30
    elif Q3 == "Some":
        trust += 15

    silo["trust"] = trust

    if trust < 40:
        twin.insights.append(Insight(
            "Low trust foundation — engagement, turnover, or role clarity issues",
            "Rule 2.1",
            "HIGH"
        ))

    # =========================================================
    # RULE 2.2 — HEALTHY CONFLICT
    # =========================================================
    conflict = 70  # default healthy

    if Q5 >= 50 and any(x in Q6 for x in [
        "Stronger leadership/management",
        "Improved communication/collaboration",
        "Better work-life balance"
    ]):
        conflict = 30

        twin.insights.append(Insight(
            "Artificial harmony detected — people not speaking up",
            "Rule 2.2",
            "HIGH"
        ))

    if Q4 == "No" and Q3 == "No":
        conflict = 20

        twin.insights.append(Insight(
            "Conflict avoidance pattern — leadership not engaging real issues",
            "Rule 2.2",
            "HIGH"
        ))

    silo["conflict"] = conflict

    # =========================================================
    # RULE 2.3 — COMMITMENT
    # =========================================================
    commitment = 0

    if Q3 == "Yes":
        commitment += 50
    elif Q3 == "Some":
        commitment += 25

    strategy_q9 = twin.silos.get("strategy", {}).get("strategy_clarity_label", "")

    if strategy_q9 == "HIGH":
        commitment += 50
    elif strategy_q9 == "MEDIUM":
        commitment += 25

    silo["commitment"] = commitment

    if commitment < 40:
        twin.insights.append(Insight(
            "Lack of Buy-In — team doesn't understand roles or direction",
            "Rule 2.3",
            "CRITICAL"
        ))

    # =========================================================
    # RULE 2.4 — ACCOUNTABILITY
    # =========================================================
    accountability = 0

    # Role clarity
    if Q3 == "Yes":
        accountability += 40
    elif Q3 == "Some":
        accountability += 20

    # Turnover impact
    if Q5 < 25:
        accountability += 30
    elif Q5 < 50:
        accountability += 15

    # Performance signals
    if any(x in Q6 for x in [
        "Clearer roles and responsibilities",
        "Better processes/workflows",
        "Stronger leadership/management"
    ]):
        accountability += 20

    elif any(x in Q6 for x in [
        "Better tools/technology",
        "Additional headcount"
    ]):
        accountability += 25

    elif any(x in Q6 for x in [
        "Recognition/appreciation",
        "More autonomy/empowerment"
    ]):
        accountability += 10

    silo["accountability"] = accountability

    if accountability < 50:
        twin.insights.append(Insight(
            "Low Standards Dysfunction — weak accountability culture",
            "Rule 2.4",
            "HIGH"
        ))

    # =========================================================
    # RULE 2.5 — RESULTS ORIENTATION
    # =========================================================
    if Q7 < 10:
        results = 90
    elif Q7 < 25:
        results = 70
    elif Q7 < 50:
        results = 50
    else:
        results = 30

        twin.insights.append(Insight(
            "Organization depends on individual heroism",
            "Rule 2.5",
            "HIGH"
        ))

    if Q7 >= 25:
        twin.insights.append(Insight(
            "Succession planning required",
            "Rule 2.5",
            "CRITICAL"
        ))

    silo["results"] = results

    # =========================================================
    # RULE 2.6 — TEAM HEALTH SCORE
    # =========================================================
    team_health = (trust + conflict + commitment + accountability + results) / 5

    silo["team_health"] = team_health
    twin.scores["team_health"] = team_health

    if team_health < 50:
        twin.insights.append(Insight(
            "Lencioni Team Health Workshop recommended",
            "Rule 2.6",
            "HIGH"
        ))

    # =========================================================
    # RULE 2.7 — TURNOVER CRISIS
    # =========================================================
    if Q5 >= 50:
        twin.insights.append(Insight(
            "Turnover crisis detected",
            "Rule 2.7",
            "CRITICAL"
        ))

        twin.risks.append(RiskItem(
            "High turnover threatens operations",
            "Almost Certain",
            "Major",
            "CRITICAL",
            "Rule 2.7"
        ))

    # =========================================================
    # RULE 2.8 — KNOWLEDGE CONCENTRATION
    # =========================================================
    if Q7 >= 25 and Q5 >= 25:
        twin.insights.append(Insight(
            "Critical succession risk — knowledge + turnover combined",
            "Rule 2.8",
            "CRITICAL"
        ))

    if Q7 > 50 and twin.silos.get("service", {}).get("quality", 0) >= 80:
        twin.insights.append(Insight(
            "Service depends on single individual — high risk",
            "Rule 2.8",
            "CRITICAL"
        ))

    # =========================================================
    # RULE 2.9 — ORGANIZATIONAL COMPLEXITY
    # =========================================================
    if Q2 >= 5 and Q1 <= 25:
        twin.insights.append(Insight(
            "Over-structured organization — too many departments",
            "Rule 2.9",
            "MEDIUM"
        ))

    if Q2 <= 2 and Q1 > 25:
        twin.insights.append(Insight(
            "Under-structured organization — unclear responsibilities",
            "Rule 2.9",
            "HIGH"
        ))

    # =========================================================
    # RULE 2.10 — ROLE CLARITY IMPACT
    # =========================================================
    if Q3 == "No":
        twin.insights.append(Insight(
            "Missing job architecture and KPIs — affecting multiple silos",
            "Rule 2.10",
            "CRITICAL"
        ))

    # =========================================================
    # SAVE SILO
    # =========================================================
    silo["turnover"] = Q5
    silo["knowledge_concentration"] = Q7

    twin.silos["hr"] = silo