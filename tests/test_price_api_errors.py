import subprocess

import pytest

from app.services import price_service
from app.services.price_service import MarketDataUnavailable

SECRET = "SUPER-SECRET-AGMARKNET-KEY-123"


class Completed:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode, self.stdout, self.stderr = returncode, stdout, stderr


@pytest.fixture(autouse=True)
def secret_key(monkeypatch):
    monkeypatch.setattr(price_service, "API_KEY", SECRET)


# ---------------------------------------------------------------- the key stays out of the logs

def test_the_api_key_is_never_printed(monkeypatch, capsys):
    def fake_run(args, **kwargs):
        # curl echoes the URL (with the key) in some errors
        return Completed(6, "", f"curl: (6) Could not resolve host for {args[-1]}")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert price_service.call_api("https://api.example/x", {"api-key": SECRET, "format": "json"}) is None

    output = capsys.readouterr().out

    assert SECRET not in output
    assert "<api-key>" in output


def test_a_bad_response_body_is_not_logged_with_the_key(monkeypatch, capsys):
    monkeypatch.setattr(
        subprocess, "run",
        lambda args, **kwargs: Completed(0, f"<html>error for key {SECRET}</html>")
    )

    assert price_service.call_api("https://api.example/x", {"api-key": SECRET}) is None
    assert SECRET not in capsys.readouterr().out


def test_curl_errors_are_shown(monkeypatch, capsys):
    monkeypatch.setattr(
        subprocess, "run",
        lambda args, **kwargs: Completed(7, "", "curl: (7) Failed to connect to api.data.gov.in")
    )

    price_service.call_api("https://api.example/x", {"api-key": SECRET})

    assert "Failed to connect to api.data.gov.in" in capsys.readouterr().out


def test_curl_is_not_silent_about_errors(monkeypatch):
    seen = {}

    def fake_run(args, **kwargs):
        seen["args"] = args
        return Completed(0, '{"status": "ok", "total": 0, "records": []}')

    monkeypatch.setattr(subprocess, "run", fake_run)

    price_service.call_api("https://api.example/x", {"api-key": SECRET})

    assert "-sS" in seen["args"]


# ---------------------------------------------------------------- "service down" is not "no markets"

def test_search_markets_reports_a_dead_service(monkeypatch):
    monkeypatch.setattr(price_service, "call_api", lambda url, params: None)

    with pytest.raises(MarketDataUnavailable):
        price_service.search_markets("tomato")


def test_search_markets_with_no_records_is_just_empty(monkeypatch):
    empty = {"status": "ok", "total": 0, "records": []}
    monkeypatch.setattr(price_service, "call_api", lambda url, params: empty)

    assert price_service.search_markets("dragonfruit") == []


def test_one_working_service_is_enough(monkeypatch):
    def fake(url, params):
        if url == price_service.CURRENT_API:
            return {"status": "ok", "records": [
                {"commodity": "Tomato", "district": "Kolar", "market": "Kolar",
                 "modal_price": "1200", "arrival_date": "01/10/2026"}
            ]}

        return None                                          # the history service is down

    monkeypatch.setattr(price_service, "call_api", fake)

    markets = price_service.search_markets("tomato")

    assert markets[0]["market"] == "Kolar"


def test_predict_price_turns_it_into_an_error_message(monkeypatch):
    monkeypatch.setattr(price_service, "call_api", lambda url, params: None)

    result = price_service.predict_price("tomato")

    assert "not responding" in result["error"]
    assert "try again later" in result["error"]


def test_the_web_route_reports_it_too(client, monkeypatch):
    monkeypatch.setattr(price_service, "call_api", lambda url, params: None)

    body = client.get("/predict-price", params={"crop": "tomato"}).json()

    assert "not responding" in body["error"]
