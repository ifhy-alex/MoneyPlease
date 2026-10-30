import base64
import email
from datetime import UTC, datetime
from email import policy
from pathlib import Path

from moneyplease.ingest.connectors.gmail_alerts import GmailAlertsConnector

FIX = Path(__file__).parent / "fixtures"


def html_of(name):
    msg = email.message_from_bytes((FIX / name).read_bytes(), policy=policy.default)
    return msg.get_body(("html",)).get_content()


def gmail_message(mid, sender, html, internal_ms):
    data = base64.urlsafe_b64encode(html.encode()).decode()
    return {"id": mid, "internalDate": str(internal_ms), "payload": {
        "mimeType": "multipart/alternative",
        "headers": [{"name": "From", "value": sender}],
        "parts": [{"mimeType": "text/plain", "body": {"data": ""}},
                  {"mimeType": "text/html", "body": {"data": data}}]}}


class Call:
    def __init__(self, value):
        self.value = value

    def execute(self):
        return self.value


class FakeService:
    def __init__(self, messages, labels=({"id": "L1", "name": "Empleo/Alertas"},)):
        self.messages_by_id = {m["id"]: m for m in messages}
        self.labels_ = list(labels)
        self.list_calls = []

    def users(self):
        return self

    def labels(self):
        svc = self

        class Labels:
            def list(self, userId):
                return Call({"labels": svc.labels_})
        return Labels()

    def messages(self):
        svc = self

        class Messages:
            def list(self, userId, labelIds, q, pageToken=None):
                svc.list_calls.append({"labelIds": labelIds, "q": q})
                return Call({"messages": [{"id": i} for i in svc.messages_by_id]} if svc.messages_by_id else {})

            def get(self, userId, id, format):
                return Call(svc.messages_by_id[id])
        return Messages()


def test_gmail_connector_uses_after_and_updates_cursor():
    svc = FakeService([
        gmail_message("m1", "jobalerts-noreply@linkedin.com", html_of("linkedin_alert.eml"), 1700000500000),
        gmail_message("m2", "alert@indeed.com", html_of("indeed_alert.eml"), 1700000900000),
    ])
    c = GmailAlertsConnector(svc, "Empleo/Alertas", {"last_internal_date_s": 1700000000})
    assert c.key == "gmail" and not c.is_complete_listing
    result = c.fetch()
    assert svc.list_calls[0] == {"labelIds": ["L1"], "q": "after:1700000000"}
    assert len(result.jobs) == 5
    assert result.config_updates == {"last_internal_date_s": 1700000900}
    li = result.jobs[0]
    assert li.published_at == datetime.fromtimestamp(1700000500, UTC)
    assert li.raw["gmail_message_id"] == "m1"


def test_gmail_connector_no_messages():
    result = GmailAlertsConnector(FakeService([]), "Empleo/Alertas", {}).fetch()
    assert result.jobs == [] and result.config_updates == {}


def test_gmail_connector_missing_label():
    result = GmailAlertsConnector(FakeService([], labels=()), "Empleo/Alertas", {}).fetch()
    assert result.jobs == [] and result.config_updates == {}
