import json
import os
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from app.db.database import clean, get_db, next_id
from app.services import digilocker, loan_advisor
from app.services.auth_service import get_current_user
from app.services.geo import bounding_box, within_radius
from app.services.translation_service import normalize_language, translate_payload

router = APIRouter(prefix="/loan")

_BANKS_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "banks_csc.json"
)

with open(_BANKS_FILE, encoding="utf-8") as f:
    _BANKS = json.load(f)

DOCUMENT_CODES = {
    "aadhaar", "pan", "voter_id", "bank_passbook", "photo",
    "land_record", "lease_agreement", "soil_health_card"
}


# ------------------------------------------------------------ request bodies

class Land(BaseModel):
    survey_number: str = Field(default="", max_length=40)
    extent_acres: float = Field(ge=0, le=10000)
    ownership: Literal["owner", "tenant", "sharecropper"] = "owner"
    irrigated: bool = False


class CropSeason(BaseModel):
    crop: str = Field(min_length=1, max_length=40)
    season: Literal["kharif", "rabi", "summer"] = "kharif"
    year: int = Field(ge=1990, le=2100)
    area_acres: float = Field(gt=0, le=10000)
    yield_quintal_per_acre: float | None = Field(default=None, ge=0, le=100000)


class PlannedCrop(BaseModel):
    crop: str = Field(min_length=1, max_length=40)
    area_acres: float = Field(gt=0, le=10000)


class Soil(BaseModel):
    ph: float | None = Field(default=None, ge=0, le=14)
    oc_percent: float | None = Field(default=None, ge=0, le=20)
    n_kg_ha: float | None = Field(default=None, ge=0, le=5000)
    p_kg_ha: float | None = Field(default=None, ge=0, le=1000)
    k_kg_ha: float | None = Field(default=None, ge=0, le=5000)
    ec_dsm: float | None = Field(default=None, ge=0, le=50)
    tested_on: str | None = None


class ProfileRequest(BaseModel):
    farmer_name: str | None = Field(default=None, max_length=80)
    age: int | None = Field(default=None, ge=0, le=120)
    district: str = Field(min_length=1, max_length=60)
    taluk: str | None = Field(default=None, max_length=60)
    village: str | None = Field(default=None, max_length=60)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)

    land: Land
    crops: list[CropSeason] = Field(default_factory=list, max_length=40)
    planned_crops: list[PlannedCrop] = Field(default_factory=list, max_length=20)
    soil: Soil | None = None

    existing_loan_outstanding: float = Field(default=0, ge=0, le=1e9)
    has_default: bool = False
    documents: list[str] = Field(default_factory=list, max_length=20)

    land_source: str = "self_declared"
    soil_source: str = "self_declared"


class DigiLockerRequest(BaseModel):
    survey_number: str = Field(min_length=1, max_length=40)
    district: str | None = None


class ReportRequest(BaseModel):
    lang: str = "en"


# ------------------------------------------------------------ profile

@router.post("/profile")
def save_profile(
    request: ProfileRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    unknown = set(request.documents) - DOCUMENT_CODES

    if unknown:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown document type: {', '.join(sorted(unknown))}"
        )

    profile = {
        **request.model_dump(mode="json"),
        "user_id": user["id"],
        "updated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }

    db.farmer_profiles.update_one(
        {"user_id": user["id"]}, {"$set": profile}, upsert=True
    )

    return {"message": "Profile saved"}


@router.get("/profile")
def get_profile(user=Depends(get_current_user), db=Depends(get_db)):
    profile = db.farmer_profiles.find_one({"user_id": user["id"]})

    if not profile:
        raise HTTPException(status_code=404, detail="No profile saved yet")

    return clean(profile)


# ------------------------------------------------------------ DigiLocker

@router.post("/digilocker/fetch")
def digilocker_fetch(
    request: DigiLockerRequest,
    user=Depends(get_current_user)
):
    """
    Land record + Soil Health Card for a survey number.
    Uses the demo provider unless a real integration is configured.
    """

    provider = digilocker.get_provider()

    try:
        land = provider.fetch_land_record(request.survey_number, request.district)
        soil = provider.fetch_soil_card(request.survey_number, request.district)

    except digilocker.DigiLockerError as e:
        raise HTTPException(status_code=502, detail=str(e))

    return {"provider": provider.name, "land": land, "soil": soil}


# ------------------------------------------------------------ report

@router.post("/report")
def create_report(
    request: ReportRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    profile = db.farmer_profiles.find_one({"user_id": user["id"]})

    if not profile:
        raise HTTPException(
            status_code=404,
            detail="Save your farm details first"
        )

    weather = loan_advisor.assess_weather_risk(profile.get("district"), db)

    report = loan_advisor.build_report(profile, weather)
    report["explanation"] = loan_advisor.explain(report)

    stored = {
        "id": next_id("loan_reports"),
        "user_id": user["id"],
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "district": profile.get("district"),
        "report": report,
    }

    db.loan_reports.insert_one(stored)

    lang = normalize_language(request.lang)

    return {
        "id": stored["id"],
        "created_at": stored["created_at"],
        "lang": lang,
        "report": translate_payload(report, lang),
    }


@router.get("/reports")
def list_reports(user=Depends(get_current_user), db=Depends(get_db)):
    return [
        clean(item)
        for item in db.loan_reports.find({"user_id": user["id"]}).sort("id", -1).limit(20)
    ]


@router.get("/reports/{report_id}")
def get_report(
    report_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    item = db.loan_reports.find_one({"id": report_id, "user_id": user["id"]})

    if not item:
        raise HTTPException(status_code=404, detail="Report not found")

    return clean(item)


# ------------------------------------------------------------ nearby branches

@router.get("/nearby")
def nearby(
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius_km: float = Query(50, gt=0, le=300),
    type: Literal["bank", "csc", "all"] = "all",
    limit: int = Query(10, ge=1, le=50),
):
    """Nearest banks and Common Service Centres (sample directory)."""

    min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)

    candidates = [
        {**entry, "location_geo": {"lat": entry["lat"], "lng": entry["lng"]}}
        for entry in _BANKS["entries"]
        if min_lat <= entry["lat"] <= max_lat
        and min_lng <= entry["lng"] <= max_lng
        and (type == "all" or entry["type"] == type)
    ]

    results = within_radius(candidates, lat, lng, radius_km)[:limit]

    for item in results:
        item.pop("location_geo", None)
        item["directions_url"] = (
            f"https://www.google.com/maps/dir/?api=1&destination={item['lat']},{item['lng']}"
        )

    is_sample = any(entry.get("sample") for entry in _BANKS["entries"])

    return {
        "data_source": "sample" if is_sample else "directory",
        "note": _BANKS["_note"] if is_sample else "",
        "results": results
    }
