"""The price page runs on the trained model in ml/. No price API may be called."""

import pytest

from app.services import price_model, price_service


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any attempt to reach the internet during a price lookup is a failure."""

    import socket
    import subprocess

    def refuse(*args, **kwargs):
        raise AssertionError("the price lookup tried to use the network")

    real_run = subprocess.run

    def run(command, *args, **kwargs):
        # curl was how the old price API was called; other subprocesses (joblib counting CPUs) are fine
        if "curl" in str(command).lower():
            refuse()

        return real_run(command, *args, **kwargs)

    real_connect = socket.socket.connect

    def connect(sock, address, *args, **kwargs):
        # asyncio uses loopback sockets internally; only a connection to another machine counts
        host = address[0] if isinstance(address, tuple) else str(address)

        if host not in ("127.0.0.1", "::1", "localhost"):
            refuse()

        return real_connect(sock, address, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", connect)
    monkeypatch.setattr(subprocess, "run", run)


def test_markets_come_from_the_model_data():
    markets = price_service.search_markets("Maize")

    assert len(markets) > 5
    assert markets[0]["district"] == "Karnataka"          # the state average first
    assert all(m["latest_price"] > 0 and m["latest_price_date"] for m in markets)
    assert {"district", "market", "current_price_available"} <= set(markets[0])


def test_crop_names_and_aliases_are_understood():
    assert price_model.resolve_crop("Maize") == "maize"
    assert price_model.resolve_crop("Bengal Gram") == "bengal_gram"
    assert price_model.resolve_crop("soybean") == "soyabean"
    assert price_model.resolve_crop("pearl millet") == "bajra"
    assert price_model.resolve_crop("tomato") is None


def test_forecast_has_four_weekly_points_with_bands():
    result = price_service.predict_price("Maize", "Mandya", "Mandya")

    assert "error" not in result
    assert [p["days"] for p in result["forecast"]] == [7, 14, 21, 28]

    for point in result["forecast"]:
        assert 0 < point["low"] < point["price"] < point["high"]

    assert result["predicted_price"] == result["forecast"][-1]["price"]
    assert result["trend"] in ("Rising", "Falling", "Stable")
    assert result["best_time_to_sell"]["action"] in ("sell_now", "wait")
    assert result["model_metrics"]["mae"] > 0
    assert result["unit"] == "₹ per quintal"


def test_forecast_stays_close_to_the_latest_price():
    result = price_service.predict_price("Rice", "Karnataka", "State average")

    # a month ahead, a mandi price does not jump by half
    assert 0.6 * result["latest_price"] < result["predicted_price"] < 1.5 * result["latest_price"]


def test_a_crop_without_a_trained_forecast_shows_typical_prices_only():
    result = price_service.predict_price("Jaggery", "Mandya", "Mandya")

    assert "error" not in result
    assert result["predicted_price"] is None
    assert result["latest_price"] > 0
    assert result["seasonal_outlook"]


def test_unknown_crops_and_places_give_clear_errors():
    unknown = price_service.predict_price("Tomato")

    # the exact text the app translates, plus the crops to suggest
    assert unknown["error"] == "No Karnataka markets found for this crop"
    assert "maize" in unknown["supported_crops"]

    assert "No market price data" in price_service.predict_price("Rice", "Atlantis", "Atlantis")["error"]
    assert price_service.predict_price("")["error"] == "Crop name is required"


def test_the_web_route_uses_the_model(client):
    markets = client.get("/predict-price", params={"crop": "Wheat"}).json()

    assert markets["markets"]

    first = markets["markets"][0]
    result = client.get("/predict-price", params={
        "crop": "Wheat", "district": first["district"], "market": first["market"]
    }).json()

    assert len(result["forecast"]) == 4


def test_a_missing_model_file_is_reported_not_crashed(monkeypatch):
    monkeypatch.setattr(price_model, "_bundle", None)
    monkeypatch.setenv("PRICE_MODEL_DIR", "does/not/exist")

    result = price_service.predict_price("Rice")

    assert "not available" in result["error"]
