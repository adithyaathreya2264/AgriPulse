import pytest

import app.services.loan_advisor as loan_advisor
import app.services.translation_service as translation
from app.services import digilocker
from app.services.loan_advisor import build_report, estimate_limit, planned_crops


def profile(**overrides):
    """A healthy, well documented farmer."""
    data = {
        "age": 40,
        "district": "Kolar",
        "land": {"survey_number": "12/3", "extent_acres": 4.0, "ownership": "owner", "irrigated": True},
        "crops": [
            {"crop": "tomato", "season": "kharif", "year": 2024, "area_acres": 2.0, "yield_quintal_per_acre": 100},
            {"crop": "ragi", "season": "kharif", "year": 2024, "area_acres": 2.0, "yield_quintal_per_acre": 10},
            {"crop": "tomato", "season": "rabi", "year": 2023, "area_acres": 2.0, "yield_quintal_per_acre": 102},
            {"crop": "ragi", "season": "kharif", "year": 2023, "area_acres": 2.0, "yield_quintal_per_acre": 10},
        ],
        "soil": {"ph": 6.5, "oc_percent": 0.8, "n_kg_ha": 300, "p_kg_ha": 20, "k_kg_ha": 200, "ec_dsm": 0.4},
        "existing_loan_outstanding": 0,
        "has_default": False,
        "documents": ["aadhaar", "bank_passbook", "photo", "land_record", "soil_health_card"],
    }
    data.update(overrides)
    return data


LOW_RISK = {"available": True, "score": 0.1, "level": "low", "notes": []}
HIGH_RISK = {"available": True, "score": 0.9, "level": "high", "notes": []}


# ---------------------------------------------------------------- limit arithmetic

def test_limit_formula_is_scale_of_finance_plus_allowances():
    crops = [{"crop": "tomato", "area_acres": 2.0}, {"crop": "ragi", "area_acres": 2.0}]

    limit = estimate_limit(profile(), crops)

    # tomato 2 x 85,000 + ragi 2 x 24,000 = 218,000 cultivation cost
    assert limit["cultivation_cost"] == 218000
    assert limit["post_harvest_allowance"] == 21800          # +10%
    assert limit["maintenance_allowance"] == 43600           # +20%
    assert limit["estimated_limit"] == 283400
    assert limit["available_limit"] == 283400
    assert limit["collateral_free"] is False                 # above Rs 2 lakh
    assert "7%" in limit["interest_note"] and "4%" in limit["interest_note"]


def test_existing_loans_reduce_the_available_limit():
    limit = estimate_limit(
        profile(existing_loan_outstanding=100000),
        [{"crop": "paddy", "area_acres": 2.0}]
    )

    assert limit["estimated_limit"] == 109200                 # 84,000 x 1.3
    assert limit["available_limit"] == 9200
    assert limit["collateral_free"] is True


def test_cropping_area_is_capped_by_land_and_intensity():
    # 4 acres of land: at most 2x cropping intensity = 8 acres
    crops = [{"crop": "paddy", "area_acres": 20.0}]

    limit = estimate_limit(profile(), crops)

    assert limit["cropped_area_acres"] == 8.0
    assert limit["cultivation_cost"] == 8 * 42000


def test_unknown_crop_uses_the_default_scale():
    limit = estimate_limit(profile(), [{"crop": "dragonfruit", "area_acres": 1.0}])

    assert limit["cultivation_cost"] == 40000


def test_planned_crops_fall_back_to_the_latest_year():
    crops = planned_crops(profile())

    assert {(c["crop"], c["area_acres"]) for c in crops} == {("tomato", 2.0), ("ragi", 2.0)}

    declared = planned_crops(profile(planned_crops=[{"crop": "onion", "area_acres": 1.5}]))
    assert declared == [{"crop": "onion", "area_acres": 1.5}]


def test_no_crops_gives_a_hint_not_a_limit():
    limit = estimate_limit(profile(crops=[]), [])

    assert limit["estimated_limit"] == 0
    assert "Add the crops" in limit["interest_note"]


# ---------------------------------------------------------------- verdicts

def test_strong_profile_is_eligible():
    report = build_report(profile(), LOW_RISK)

    assert report["verdict_code"] == "eligible"
    assert report["score"] >= 70
    assert report["blockers"] == []
    assert report["data_sources"]["verified"] is False
    assert "not a bank decision" in report["disclaimer"]


def test_default_blocks_eligibility():
    report = build_report(profile(has_default=True), LOW_RISK)

    assert report["verdict_code"] == "not_eligible"
    assert any("default" in blocker for blocker in report["blockers"])
    assert report["score_breakdown"]["credit_history"]["score"] == 0


def test_no_land_blocks_eligibility():
    report = build_report(
        profile(land={"survey_number": "", "extent_acres": 0, "ownership": "owner"}), LOW_RISK
    )

    assert report["verdict_code"] == "not_eligible"


def test_age_outside_the_policy_range_is_flagged():
    assert build_report(profile(age=16), LOW_RISK)["verdict_code"] == "not_eligible"
    assert build_report(profile(age=80), LOW_RISK)["verdict_code"] == "not_eligible"
    assert build_report(profile(age=None), LOW_RISK)["verdict_code"] == "eligible"


def test_missing_land_record_is_conditional_with_a_clear_tip():
    documents = ["aadhaar", "bank_passbook", "photo", "soil_health_card"]

    report = build_report(profile(documents=documents), LOW_RISK)

    assert report["verdict_code"] == "conditional"
    assert [d["code"] for d in report["missing_documents"]] == ["land_record"]
    assert "Land proof" in report["improvement_tips"][0]


def test_tenant_needs_a_lease_agreement_not_an_rtc():
    tenant = profile(
        land={"survey_number": "1", "extent_acres": 3, "ownership": "tenant"},
        documents=["aadhaar", "bank_passbook", "photo", "land_record"],
    )

    report = build_report(tenant, LOW_RISK)

    assert [d["code"] for d in report["missing_documents"]] == ["lease_agreement"]
    assert report["verdict_code"] == "conditional"

    tenant["documents"].append("lease_agreement")
    assert build_report(tenant, LOW_RISK)["missing_documents"] == []


def test_weather_risk_changes_the_score():
    safe = build_report(profile(), LOW_RISK)
    risky = build_report(profile(), HIGH_RISK)

    assert safe["score"] > risky["score"]
    assert any("insurance" in tip.lower() for tip in risky["improvement_tips"])


def test_missing_soil_card_lowers_the_score_and_adds_a_tip():
    with_soil = build_report(profile(), LOW_RISK)
    without = build_report(profile(soil=None), LOW_RISK)

    assert without["score"] < with_soil["score"]
    assert without["soil"] is None
    assert any("Soil Health Card" in tip for tip in without["improvement_tips"])


def test_poor_soil_gives_specific_advice():
    poor = profile(soil={"ph": 4.5, "oc_percent": 0.2, "n_kg_ha": 100, "p_kg_ha": 3, "k_kg_ha": 50, "ec_dsm": 2.0})

    report = build_report(poor, LOW_RISK)
    tips = " ".join(report["improvement_tips"])

    assert report["soil"]["ratings"]["n_kg_ha"] == "low"
    assert "nitrogen" in tips
    assert "pH" in tips
    assert "salinity" in tips


def test_steady_yields_score_higher_than_erratic_ones():
    erratic = profile(crops=[
        {"crop": "tomato", "season": "kharif", "year": 2024, "area_acres": 2, "yield_quintal_per_acre": 200},
        {"crop": "tomato", "season": "rabi", "year": 2023, "area_acres": 2, "yield_quintal_per_acre": 20},
        {"crop": "ragi", "season": "kharif", "year": 2023, "area_acres": 2, "yield_quintal_per_acre": 10},
        {"crop": "ragi", "season": "kharif", "year": 2022, "area_acres": 2, "yield_quintal_per_acre": 60},
    ])

    steady = build_report(profile(), LOW_RISK)["score_breakdown"]["farming_record"]["score"]
    unsteady = build_report(erratic, LOW_RISK)["score_breakdown"]["farming_record"]["score"]

    assert steady > unsteady


def test_heavy_existing_debt_lowers_the_credit_score():
    light = build_report(profile(), LOW_RISK)
    heavy = build_report(profile(existing_loan_outstanding=400000), LOW_RISK)

    assert heavy["score_breakdown"]["credit_history"]["score"] < light["score_breakdown"]["credit_history"]["score"]
    assert any("existing loans" in tip for tip in heavy["improvement_tips"])


def test_score_breakdown_adds_up_and_respects_the_maximums():
    report = build_report(profile(), LOW_RISK)
    parts = report["score_breakdown"].values()

    assert all(0 <= part["score"] <= part["max"] for part in parts)
    assert sum(part["max"] for part in parts) == 100
    assert report["score"] == round(sum(part["score"] for part in parts))


def test_tips_have_no_duplicates():
    report = build_report(profile(soil=None, documents=[]), HIGH_RISK)

    assert len(report["improvement_tips"]) == len(set(report["improvement_tips"]))


# ---------------------------------------------------------------- explanation

def test_explanation_uses_gemini_and_falls_back(monkeypatch):
    report = build_report(profile(), LOW_RISK)

    class Fake:
        text = "You look eligible. Estimated limit is Rs 2.8 lakh."

    monkeypatch.setattr(loan_advisor, "generate_content", lambda prompt: Fake())
    assert loan_advisor.explain(report) == "You look eligible. Estimated limit is Rs 2.8 lakh."

    def boom(prompt):
        raise RuntimeError("down")

    monkeypatch.setattr(loan_advisor, "generate_content", boom)
    fallback = loan_advisor.explain(report)

    assert "Eligible" in fallback and "283,400" in fallback


# ---------------------------------------------------------------- weather risk

def test_weather_risk_is_unknown_without_data(monkeypatch):
    import app.services.weather_history_service as weather_history

    monkeypatch.setattr(weather_history, "get_weather_history", lambda *args: None)

    risk = loan_advisor.assess_weather_risk("Kolar")

    assert risk["available"] is False
    assert risk["level"] == "unknown"
    assert risk["score"] == 0.5


def test_weather_risk_reflects_rainfall_variability(monkeypatch):
    import numpy as np
    import pandas as pd

    import app.services.weather_history_service as weather_history

    index = pd.date_range("2022-01-01", "2025-06-30", freq="D")

    def frame(rain_by_year):
        rain = np.array([
            rain_by_year.get(day.year, 1.0) if 6 <= day.month <= 9 else 0.0
            for day in index
        ])
        return pd.DataFrame({"rain": rain, "temp": 27.0}, index=index)

    steady = frame({2022: 5.0, 2023: 5.0, 2024: 5.0, 2025: 5.0})
    erratic = frame({2022: 10.0, 2023: 1.0, 2024: 12.0, 2025: 0.5})

    monkeypatch.setattr(weather_history, "get_weather_history", lambda *args: steady)
    calm = loan_advisor.assess_weather_risk("Kolar")

    monkeypatch.setattr(weather_history, "get_weather_history", lambda *args: erratic)
    wild = loan_advisor.assess_weather_risk("Kolar")

    assert calm["available"] and wild["available"]
    assert calm["level"] == "low"
    assert wild["score"] > calm["score"]


# ---------------------------------------------------------------- DigiLocker adapter

def test_mock_provider_is_deterministic_and_labelled_unverified():
    provider = digilocker.MockDigiLockerProvider()

    first = provider.fetch_land_record("55/2", "Kolar")
    second = provider.fetch_land_record("55/2", "Kolar")
    other = provider.fetch_land_record("56/1", "Kolar")

    assert first == second
    assert first != other
    assert first["source"] == "mock" and first["verified"] is False
    assert 1.0 <= first["extent_acres"] <= 8.0

    soil = provider.fetch_soil_card("55/2")
    assert soil["source"] == "mock" and 5.6 <= soil["ph"] <= 7.8


def test_provider_needs_a_survey_number():
    with pytest.raises(digilocker.DigiLockerError):
        digilocker.MockDigiLockerProvider().fetch_land_record("  ")


def test_real_provider_reports_it_is_not_ready(monkeypatch):
    monkeypatch.setenv("DIGILOCKER_PROVIDER", "real")
    monkeypatch.delenv("DIGILOCKER_CLIENT_ID", raising=False)

    provider = digilocker.get_provider()

    assert provider.name == "real"

    with pytest.raises(digilocker.DigiLockerError, match="not configured"):
        provider.fetch_land_record("1")


# ---------------------------------------------------------------- routes

PROFILE_BODY = {
    "farmer_name": "Ramu",
    "age": 40,
    "district": "Kolar",
    "land": {"survey_number": "12/3", "extent_acres": 4, "ownership": "owner", "irrigated": True},
    "crops": [
        {"crop": "tomato", "season": "kharif", "year": 2024, "area_acres": 2, "yield_quintal_per_acre": 100},
        {"crop": "ragi", "season": "kharif", "year": 2024, "area_acres": 2, "yield_quintal_per_acre": 10},
    ],
    "soil": {"ph": 6.5, "oc_percent": 0.8, "n_kg_ha": 300, "p_kg_ha": 20, "k_kg_ha": 200, "ec_dsm": 0.4},
    "documents": ["aadhaar", "bank_passbook", "photo", "land_record"],
}


@pytest.fixture
def no_ai(monkeypatch):
    """No Gemini, no weather download."""
    monkeypatch.setattr(loan_advisor, "generate_content", lambda prompt: (_ for _ in ()).throw(RuntimeError("off")))
    monkeypatch.setattr(loan_advisor, "assess_weather_risk", lambda district, db=None, years=3: LOW_RISK)


def test_loan_routes_require_login(client):
    assert client.post("/loan/profile", json=PROFILE_BODY).status_code == 401
    assert client.post("/loan/report", json={}).status_code == 401
    assert client.get("/loan/reports").status_code == 401
    assert client.post("/loan/digilocker/fetch", json={"survey_number": "1"}).status_code == 401


def test_report_needs_a_saved_profile(client, renter, no_ai):
    assert client.post("/loan/report", json={}, headers=renter["headers"]).status_code == 404


def test_full_flow_profile_report_history(client, renter, no_ai):
    saved = client.post("/loan/profile", json=PROFILE_BODY, headers=renter["headers"])
    assert saved.status_code == 200

    assert client.get("/loan/profile", headers=renter["headers"]).json()["district"] == "Kolar"

    response = client.post("/loan/report", json={"lang": "en"}, headers=renter["headers"])

    assert response.status_code == 200
    body = response.json()
    report = body["report"]

    assert report["verdict_code"] == "eligible"
    assert report["estimated_limit"]["estimated_limit"] == 283400
    assert "Eligible" in report["explanation"]           # template fallback

    history = client.get("/loan/reports", headers=renter["headers"]).json()
    assert len(history) == 1 and history[0]["id"] == body["id"]


def test_report_is_translated_but_stored_in_english(client, renter, no_ai, monkeypatch):
    client.post("/loan/profile", json=PROFILE_BODY, headers=renter["headers"])

    monkeypatch.setattr(
        translation, "_translate_list",
        lambda texts, lang: [f"[{lang}] {text}" for text in texts]
    )

    body = client.post("/loan/report", json={"lang": "kn"}, headers=renter["headers"]).json()

    assert body["report"]["verdict"] == "[kn] Eligible"
    assert body["report"]["estimated_limit"]["estimated_limit"] == 283400      # numbers untouched

    stored = client.get(f"/loan/reports/{body['id']}", headers=renter["headers"]).json()
    assert stored["report"]["verdict"] == "Eligible"


def test_reports_are_private(client, renter, other, no_ai):
    client.post("/loan/profile", json=PROFILE_BODY, headers=renter["headers"])
    report_id = client.post("/loan/report", json={}, headers=renter["headers"]).json()["id"]

    assert client.get("/loan/reports", headers=other["headers"]).json() == []
    assert client.get(f"/loan/reports/{report_id}", headers=other["headers"]).status_code == 404


def test_profile_validation(client, renter):
    bad_ph = {**PROFILE_BODY, "soil": {"ph": 40}}
    assert client.post("/loan/profile", json=bad_ph, headers=renter["headers"]).status_code == 422

    negative = {**PROFILE_BODY, "land": {"extent_acres": -2}}
    assert client.post("/loan/profile", json=negative, headers=renter["headers"]).status_code == 422

    bad_doc = {**PROFILE_BODY, "documents": ["aadhaar", "library_card"]}
    response = client.post("/loan/profile", json=bad_doc, headers=renter["headers"])
    assert response.status_code == 400 and "library_card" in response.json()["detail"]


def test_saving_a_profile_twice_updates_it(client, renter):
    client.post("/loan/profile", json=PROFILE_BODY, headers=renter["headers"])
    client.post("/loan/profile", json={**PROFILE_BODY, "district": "Mandya"}, headers=renter["headers"])

    import app.db.database as database

    assert database.get_database().farmer_profiles.count_documents({}) == 1
    assert client.get("/loan/profile", headers=renter["headers"]).json()["district"] == "Mandya"


def test_digilocker_route_returns_labelled_demo_data(client, renter):
    body = client.post(
        "/loan/digilocker/fetch",
        json={"survey_number": "88/1", "district": "Kolar"},
        headers=renter["headers"]
    ).json()

    assert body["provider"] == "mock"
    assert body["land"]["verified"] is False
    assert body["soil"]["source"] == "mock"


# ---------------------------------------------------------------- nearby banks / CSCs

def test_nearby_returns_sorted_results_with_directions(client):
    kolar = (13.1357, 78.1326)

    body = client.get("/loan/nearby", params={"lat": kolar[0], "lng": kolar[1], "radius_km": 20}).json()

    assert body["data_source"] == "sample"
    assert body["results"]

    distances = [item["distance_km"] for item in body["results"]]
    assert distances == sorted(distances)
    assert all(item["district"] == "Kolar" for item in body["results"])
    assert "google.com/maps" in body["results"][0]["directions_url"]


def test_nearby_filters_by_type_and_limit(client):
    kolar = (13.1357, 78.1326)

    csc = client.get(
        "/loan/nearby", params={"lat": kolar[0], "lng": kolar[1], "type": "csc"}
    ).json()["results"]

    assert csc and all(item["type"] == "csc" for item in csc)

    limited = client.get(
        "/loan/nearby", params={"lat": kolar[0], "lng": kolar[1], "limit": 2}
    ).json()["results"]

    assert len(limited) == 2


def test_nearby_far_from_karnataka_is_empty(client):
    assert client.get("/loan/nearby", params={"lat": 28.6, "lng": 77.2, "radius_km": 30}).json()["results"] == []
