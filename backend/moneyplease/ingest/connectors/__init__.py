from datetime import date

from moneyplease.config import Settings
from moneyplease.db.models import Source
from moneyplease.ingest.base import Connector
from moneyplease.ingest.connectors.gmail_alerts import GmailAlertsConnector, build_service
from moneyplease.ingest.connectors.greenhouse import GreenhouseConnector
from moneyplease.ingest.connectors.jsearch import JSearchConnector
from moneyplease.ingest.connectors.lever import LeverConnector
from moneyplease.ingest.connectors.workday import WorkdayConnector
from moneyplease.ingest.http import PoliteClient

ATS = {"greenhouse": GreenhouseConnector, "lever": LeverConnector}


def build_connector(source: Source, settings: Settings, client: PoliteClient, today: date) -> Connector | None:
    """Conector para la fuente, o None si le faltan credenciales o está sin cuota."""
    config = source.config_json or {}
    until = config.get("quota_exhausted_until")
    if until and date.fromisoformat(until) > today:
        return None
    ats = source.key.partition(":")[0]
    if ats == "workday":
        return WorkdayConnector(config["slug"], config["wd"], config["site"], source.nombre, client)
    if ats in ATS:
        return ATS[ats](config["slug"], source.nombre, client)
    if source.key == "jsearch":
        return JSearchConnector(settings.jsearch_api_key, config, client, today) if settings.jsearch_api_key else None
    if source.key == "gmail":
        service = build_service(settings)
        return GmailAlertsConnector(service, settings.gmail_label, config) if service else None
    return None
