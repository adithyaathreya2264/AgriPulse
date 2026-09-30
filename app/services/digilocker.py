"""
DigiLocker adapter for land records and the Soil Health Card.

The real DigiLocker / Bhoomi / Soil Health Card APIs are only available to
onboarded government partners, so this project ships a MOCK provider and
a stub for the real one behind the same interface:

    DIGILOCKER_PROVIDER=mock   (default)   sample data, clearly labelled
    DIGILOCKER_PROVIDER=real               needs DIGILOCKER_CLIENT_ID / _SECRET

Every result carries `source` and `verified` so a report can never present
demo data as verified.
"""

import hashlib
import os
from abc import ABC, abstractmethod


class DigiLockerError(RuntimeError):
    """The provider could not return a record."""


class DigiLockerProvider(ABC):
    name = "abstract"

    @abstractmethod
    def fetch_land_record(self, survey_number, district=None):
        """-> dict: survey_number, extent_acres, ownership, owner_name, irrigated ..."""

    @abstractmethod
    def fetch_soil_card(self, survey_number, district=None):
        """-> dict: ph, oc_percent, n_kg_ha, p_kg_ha, k_kg_ha, ec_dsm, tested_on ..."""


def _unit(seed, index):
    """Deterministic float in [0, 1) from a survey number."""
    digest = hashlib.sha256(f"{seed}:{index}".encode()).digest()
    return int.from_bytes(digest[:4], "big") / 2 ** 32


class MockDigiLockerProvider(DigiLockerProvider):
    """Deterministic sample data: the same survey number always gives the same record."""

    name = "mock"

    def _check(self, survey_number):
        if not survey_number or not str(survey_number).strip():
            raise DigiLockerError("Survey number is required")

    def fetch_land_record(self, survey_number, district=None):
        self._check(survey_number)
        key = str(survey_number).strip().lower()

        return {
            "source": "mock",
            "verified": False,
            "survey_number": str(survey_number).strip(),
            "district": district,
            "owner_name": "Sample Farmer",
            "ownership": "owner",
            "extent_acres": round(1.0 + _unit(key, 1) * 7, 2),
            "irrigated": _unit(key, 2) > 0.5,
            "note": "Demo record. Not a real land record."
        }

    def fetch_soil_card(self, survey_number, district=None):
        self._check(survey_number)
        key = str(survey_number).strip().lower()

        return {
            "source": "mock",
            "verified": False,
            "survey_number": str(survey_number).strip(),
            "ph": round(5.6 + _unit(key, 3) * 2.2, 1),
            "oc_percent": round(0.3 + _unit(key, 4) * 0.7, 2),
            "n_kg_ha": round(200 + _unit(key, 5) * 400),
            "p_kg_ha": round(6 + _unit(key, 6) * 30),
            "k_kg_ha": round(80 + _unit(key, 7) * 260),
            "ec_dsm": round(0.2 + _unit(key, 8) * 0.8, 2),
            "tested_on": None,
            "note": "Demo soil card. Not a real Soil Health Card."
        }


class RealDigiLockerProvider(DigiLockerProvider):
    """
    Placeholder for the real integration.

    To implement: register as a DigiLocker "Requester", obtain the client
    id / secret, run the OAuth flow so the farmer consents, then fetch the
    RTC (Bhoomi) and Soil Health Card documents with the access token.
    """

    name = "real"

    def __init__(self):
        self.client_id = os.getenv("DIGILOCKER_CLIENT_ID")
        self.client_secret = os.getenv("DIGILOCKER_CLIENT_SECRET")

    def _not_ready(self):
        if not (self.client_id and self.client_secret):
            raise DigiLockerError(
                "DigiLocker credentials are not configured "
                "(DIGILOCKER_CLIENT_ID / DIGILOCKER_CLIENT_SECRET)."
            )

        raise DigiLockerError(
            "The real DigiLocker integration is not implemented yet."
        )

    def fetch_land_record(self, survey_number, district=None):
        self._not_ready()

    def fetch_soil_card(self, survey_number, district=None):
        self._not_ready()


def get_provider():
    if os.getenv("DIGILOCKER_PROVIDER", "mock").strip().lower() == "real":
        return RealDigiLockerProvider()

    return MockDigiLockerProvider()
