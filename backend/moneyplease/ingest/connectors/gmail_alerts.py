import base64
import logging
from datetime import UTC, datetime

from moneyplease.config import Settings
from moneyplease.ingest.base import ConnectorResult
from moneyplease.ingest.connectors.email_parsers import parse_alert

log = logging.getLogger(__name__)
SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _html_part(payload: dict) -> str:
    if payload.get("mimeType") == "text/html":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4)).decode("utf-8", "replace")
    for part in payload.get("parts") or []:
        html = _html_part(part)
        if html:
            return html
    return ""


def _header(payload: dict, name: str) -> str:
    for h in payload.get("headers") or []:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


class GmailAlertsConnector:
    key = "gmail"
    is_complete_listing = False

    def __init__(self, service, label: str, config: dict):
        self.service = service
        self.label = label
        self.config = config

    def fetch(self) -> ConnectorResult:
        users = self.service.users()
        labels = users.labels().list(userId="me").execute().get("labels", [])
        label_id = next((lb["id"] for lb in labels if lb["name"] == self.label), None)
        if label_id is None:
            log.warning("No existe la etiqueta de Gmail %r", self.label)
            return ConnectorResult([])
        query = f"after:{self.config.get('last_internal_date_s', 0)}"
        ids, token = [], None
        while True:
            page = users.messages().list(userId="me", labelIds=[label_id], q=query, pageToken=token).execute()
            ids += [m["id"] for m in page.get("messages", [])]
            token = page.get("nextPageToken")
            if not token:
                break
        jobs, newest = [], None
        for mid in ids:
            msg = users.messages().get(userId="me", id=mid, format="full").execute()
            internal_ms = int(msg["internalDate"])
            newest = max(newest or 0, internal_ms)
            payload = msg["payload"]
            for job in parse_alert(_header(payload, "From"), _html_part(payload)):
                job.published_at = datetime.fromtimestamp(internal_ms / 1000, UTC)
                job.raw["gmail_message_id"] = mid
                jobs.append(job)
        updates = {"last_internal_date_s": newest // 1000} if newest else {}
        return ConnectorResult(jobs, updates)


def build_service(settings: Settings):
    """Servicio de Gmail con el token guardado; None si todavía no se autorizó."""
    if not settings.gmail_token_path.exists():
        return None
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build

    creds = Credentials.from_authorized_user_file(str(settings.gmail_token_path), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        try:
            settings.gmail_token_path.write_text(creds.to_json())
        except OSError:
            log.info("No se pudo guardar el token refrescado (secrets/ de solo lectura); se usa en memoria")
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def authorize(settings: Settings) -> None:
    from google_auth_oauthlib.flow import InstalledAppFlow

    flow = InstalledAppFlow.from_client_secrets_file(str(settings.gmail_credentials_path), SCOPES)
    creds = flow.run_local_server(port=0)
    settings.gmail_token_path.parent.mkdir(parents=True, exist_ok=True)
    settings.gmail_token_path.write_text(creds.to_json())
