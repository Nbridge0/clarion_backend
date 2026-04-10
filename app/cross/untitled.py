def run_cross_rules(twin):

    # CS.4 — Turnover cascade
    hr = twin.silos.get("hr", {})
    if hr.get("turnover", 0) >= 50:
        twin.insights.append({
            "message": "High turnover is degrading service quality and operations",
            "sourceRule": "CS.4",
            "priority": "CRITICAL"
        })

    # CS.3 — Growth vs runway
    strategy = twin.silos.get("strategy", {})
    risk = twin.silos.get("risk", {})

    if strategy.get("growth_confidence", 0) >= 4 and risk.get("runway", 12) < 6:
        twin.insights.append({
            "message": "Growth ambition exceeds financial runway",
            "sourceRule": "CS.3",
            "priority": "CRITICAL"
        })