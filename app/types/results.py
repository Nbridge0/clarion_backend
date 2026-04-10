from typing import Literal

RiskLevel = Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]

class RiskItem:
    def __init__(self, name, likelihood, impact, rating, source, category=None):
        self.name = name
        self.likelihood = likelihood
        self.impact = impact
        self.rating = rating
        self.source = source
        self.category = category


class Insight:
    def __init__(self, message, source_rule, priority=None):
        self.message = message
        self.source_rule = source_rule
        self.priority = priority