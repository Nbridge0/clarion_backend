from app.types.results import RiskItem, Insight


class DigitalTwin:
    def __init__(self):
        self.silos = {
            "strategy": {},
            "hr": {},
            "efficiency": {},
            "financial": {},
            "marketing": {},
            "service": {},
            "risk": {}
        }

        self.scores = {}

        self.swot = {
            "strengths": [],
            "weaknesses": [],
            "opportunities": [],
            "threats": []
        }

        self.risks = []
        self.insights = []