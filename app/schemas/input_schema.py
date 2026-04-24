from pydantic import BaseModel, Field
from typing import List, Optional


class ClarionInput(BaseModel):
    # -----------------------------
    # MARKET / STRATEGY
    # -----------------------------
    q3_competitors: List[str] = Field(default_factory=list)

    q5_competitive_advantage: List[str] = Field(default_factory=list)

    q6_growth_confidence: int = Field(default=3, ge=1, le=5)

    q7_admin_percent: int = Field(default=50, ge=0, le=100)

    q7_strength: Optional[str] = None

    q8_duplication: str = Field(default="Some")  # None / Some / A lot

    q9_employee_understanding: str = Field(default="No")  # Yes / Some / No

    q10_written_strategy: str = Field(default="No")  # Yes / No

    q11_growth_opportunities: List[str] = Field(default_factory=list)

    q12_owner_dependency: str = Field(default="Some")  # Yes / Some / No

    # -----------------------------
    # PEOPLE (SILO 2)
    # -----------------------------
    q13_team_size: Optional[int] = 0

    q14_hiring_difficulty: Optional[str] = "Medium"  # Low / Medium / High

    q15_employee_turnover: Optional[str] = "Medium"  # Low / Medium / High

    q16_training_level: Optional[str] = "Medium"  # Low / Medium / High

    # -----------------------------
    # OPERATIONS (SILO 3)
    # -----------------------------
    q17_process_documentation: Optional[str] = "Partial"  # Yes / Partial / No

    q18_systems_integration: Optional[str] = "Partial"  # Yes / Partial / No

    # -----------------------------
    # FINANCE (SILO 4)
    # -----------------------------
    q19_profit_margin: Optional[float] = 10.0

    q20_cash_flow_stability: Optional[str] = "Medium"  # Strong / Medium / Weak

    # -----------------------------
    # MARKETING (SILO 5)
    # -----------------------------
    q21_lead_generation: Optional[str] = "Inconsistent"  # Strong / Inconsistent / Weak

    q22_conversion_rate: Optional[str] = "Medium"  # High / Medium / Low

    # -----------------------------
    # SERVICE (SILO 6)
    # -----------------------------
    q23_customer_satisfaction: Optional[int] = 3  # 1–5

    q24_retention_rate: Optional[str] = "Medium"  # High / Medium / Low

    # -----------------------------
    # RISK (SILO 7)
    # -----------------------------
    q25_legal_risk: Optional[str] = "Low"  # Low / Medium / High

    q26_financial_risk: Optional[str] = "Medium"  # Low / Medium / High

    q27_operational_risk: Optional[str] = "Medium"  # Low / Medium / High

    # -----------------------------
    # GLOBAL VALIDATION (OPTIONAL)
    # -----------------------------
    def normalize(self):
        """
        Optional normalization step
        """
        if self.q10_written_strategy:
            self.q10_written_strategy = self.q10_written_strategy.capitalize()

        if self.q9_employee_understanding:
            self.q9_employee_understanding = self.q9_employee_understanding.capitalize()

        return self