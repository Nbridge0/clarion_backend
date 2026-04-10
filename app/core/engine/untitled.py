from app.core.models.digital_twin import DigitalTwin

# silos (we will build ALL)
from app.silos.silo1_strategy import process_strategy_silo
from app.silos.silo2_hr import process_hr_silo
from app.silos.silo3_efficiency import process_efficiency_silo
from app.silos.silo4_financial import process_financial_silo
from app.silos.silo5_marketing import process_marketing_silo
from app.silos.silo6_service import process_service_silo
from app.silos.silo7_risk import process_risk_silo

# cross rules
from app.cross.cross_rules import run_cross_rules


def run_engine(data):
    twin = DigitalTwin()

    # SILOS
    process_strategy_silo(data["strategy"], twin)
    process_hr_silo(data["hr"], twin)
    process_efficiency_silo(data["efficiency"], twin)
    process_financial_silo(data["financial"], twin)
    process_marketing_silo(data["marketing"], twin)
    process_service_silo(data["service"], twin)
    process_risk_silo(data["risk"], twin)

    # CROSS SILO
    run_cross_rules(twin)

    return twin