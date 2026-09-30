"""
Kisan Credit Card (KCC) eligibility advisor.

Turns a farmer's profile (land, crop history, soil health card, dues,
documents) plus a weather-risk score into:
  - an eligibility verdict and a 0-100 score with the reasons
  - an ESTIMATED credit limit (scale of finance x area, plus the standard
    post-harvest and maintenance allowances)
  - missing documents and practical tips

IMPORTANT: this is advisory. Scale-of-finance figures and policy limits in
app/data/kcc_rules.json are illustrative and must be replaced with the
official DLTC / RBI values; the bank makes the actual decision.
"""

import json
import os
import statistics
from datetime import date, timedelta
from functools import lru_cache

from app.ai.gemini_client import generate_content

DISCLAIMER = (
    "This is an advisory estimate, not a bank decision. The bank verifies "
    "your documents and sets the final limit."
)

_RULES_FILE = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "data", "kcc_rules.json"
)

DOCUMENT_POINTS = 30
CREDIT_POINTS = 25
TRACK_RECORD_POINTS = 20
SOIL_POINTS = 10
WEATHER_POINTS = 15

ELIGIBLE_SCORE = 70


@lru_cache(maxsize=1)
def load_rules():
    with open(_RULES_FILE, encoding="utf-8") as f:
        return json.load(f)


def crop_info(name, rules=None):
    rules = rules or load_rules()
    return rules["crops"].get((name or "").strip().lower(), rules["default_crop"])


# ------------------------------------------------------------------
# Weather risk
# ------------------------------------------------------------------

def _unknown_weather(reason):
    return {
        "available": False,
        "score": 0.5,
        "level": "unknown",
        "notes": [reason]
    }


def assess_weather_risk(district, db=None, years=3):
    """
    0 (safe) .. 1 (risky) from the last few years of rain and heat:
    monsoon rainfall variability, drought years and very hot days.
    """

    from app.services.weather_history_service import get_weather_history

    end = date.today() - timedelta(days=4)
    start = date(end.year - years, 1, 1)

    try:
        frame = get_weather_history(district, start, end, db)
    except Exception as e:
        print("Weather risk error:", e)
        frame = None

    if frame is None or len(frame) < 365:
        return _unknown_weather("Weather history is not available for this district")

    monsoon = frame[(frame.index.month >= 6) & (frame.index.month <= 9)]

    totals = monsoon.groupby(monsoon.index.year)["rain"].sum()
    days = monsoon.groupby(monsoon.index.year)["rain"].count()

    # Only years with (almost) the whole monsoon recorded
    totals = totals[days >= 100]

    if len(totals) < 2:
        return _unknown_weather("Not enough monsoon data to judge the rainfall")

    mean = float(totals.mean())
    variability = float(totals.std() / mean) if mean > 0 else 1.0
    drought_years = int((totals < 0.75 * mean).sum())
    hot_fraction = float((frame["temp"] > 33).mean())

    score = (
        0.5 * min(variability / 0.4, 1)
        + 0.3 * (drought_years / len(totals))
        + 0.2 * min(hot_fraction / 0.15, 1)
    )
    score = round(min(max(score, 0.0), 1.0), 2)

    notes = [
        f"Monsoon rainfall varied by {variability * 100:.0f}% between years",
        f"{drought_years} of the last {len(totals)} monsoons were dry (below 75% of normal)",
    ]

    return {
        "available": True,
        "score": score,
        "level": "low" if score < 0.33 else "moderate" if score < 0.66 else "high",
        "notes": notes,
        "average_monsoon_rain_mm": round(mean),
    }


# ------------------------------------------------------------------
# Soil
# ------------------------------------------------------------------

def _rate(value, thresholds):
    if value is None:
        return None

    if value < thresholds["low_below"]:
        return "low"

    if value > thresholds["high_above"]:
        return "high"

    return "medium"


def assess_soil(soil, planned_crops, rules=None):
    """
    Soil Health Card ratings and a 0..1 suitability score.
    Returns None when there is no soil card.
    """

    rules = rules or load_rules()

    if not soil:
        return None

    thresholds = rules["soil_thresholds"]

    ratings = {
        key: _rate(soil.get(key), thresholds[key])
        for key in ("oc_percent", "n_kg_ha", "p_kg_ha", "k_kg_ha")
    }

    points = []
    tips = []

    for key, rating in ratings.items():
        if rating is None:
            continue

        points.append(0.4 if rating == "low" else 1.0)

    nutrient_names = {
        "oc_percent": "organic carbon",
        "n_kg_ha": "nitrogen",
        "p_kg_ha": "phosphorus",
        "k_kg_ha": "potassium",
    }

    for key, rating in ratings.items():
        if rating == "low":
            tips.append(
                f"Soil {nutrient_names[key]} is low: add compost/farmyard manure "
                "and follow the fertiliser advice on your Soil Health Card."
            )

    ph = soil.get("ph")

    if ph is not None:
        crops = planned_crops or []
        in_range = [
            crop_info(item["crop"], rules)["ph"][0] <= ph <= crop_info(item["crop"], rules)["ph"][1]
            for item in crops
        ]

        if in_range:
            points.append(sum(in_range) / len(in_range))

            if not all(in_range):
                tips.append(
                    f"Soil pH {ph} is outside the best range for some of your crops. "
                    "Lime (acidic soil) or gypsum/organic matter (alkaline soil) can help."
                )
        else:
            points.append(1.0 if 6.0 <= ph <= 7.5 else 0.6)

    ec = soil.get("ec_dsm")

    if ec is not None:
        points.append(1.0 if ec < 1.0 else 0.4)

        if ec >= 1.0:
            tips.append("Soil salinity (EC) is high: improve drainage and use salt-tolerant crops.")

    return {
        "ratings": ratings,
        "ph": ph,
        "suitability": round(sum(points) / len(points), 2) if points else 0.5,
        "tips": tips,
    }


def soil_card_is_current(soil, rules=None):
    """A Soil Health Card older than the validity period should be renewed."""

    rules = rules or load_rules()

    tested_on = (soil or {}).get("tested_on")

    if not tested_on:
        return True                     # date unknown: do not penalise

    try:
        age_days = (date.today() - date.fromisoformat(str(tested_on)[:10])).days
    except ValueError:
        return True

    return age_days <= rules["policy"]["soil_card_valid_years"] * 365


# ------------------------------------------------------------------
# Limit
# ------------------------------------------------------------------

def planned_crops(profile):
    """Crops for the coming season: declared, else the latest year grown."""

    declared = profile.get("planned_crops") or []

    if declared:
        return [
            {"crop": item["crop"], "area_acres": float(item["area_acres"])}
            for item in declared
        ]

    history = profile.get("crops") or []

    if not history:
        return []

    latest_year = max(item.get("year") or 0 for item in history)

    return [
        {"crop": item["crop"], "area_acres": float(item["area_acres"])}
        for item in history
        if (item.get("year") or 0) == latest_year
    ]


def estimate_limit(profile, crops, rules=None):
    rules = rules or load_rules()
    limit_rules = rules["limit_rules"]
    policy = rules["policy"]

    extent = float((profile.get("land") or {}).get("extent_acres") or 0)
    total_area = sum(item["area_acres"] for item in crops)

    # A plot can be cropped more than once a year, but only up to a limit
    max_area = extent * limit_rules["max_cropping_intensity"]
    scale = min(1.0, max_area / total_area) if total_area > 0 else 1.0

    cultivation = sum(
        item["area_acres"] * scale * crop_info(item["crop"], rules)["scale_of_finance"]
        for item in crops
    )

    post_harvest = cultivation * limit_rules["post_harvest_percent"] / 100
    maintenance = cultivation * limit_rules["maintenance_percent"] / 100
    total = cultivation + post_harvest + maintenance

    outstanding = float(profile.get("existing_loan_outstanding") or 0)
    available = max(total - outstanding, 0)

    if total <= 0:
        interest = "Add the crops you plan to grow to get a limit estimate."
    elif total <= policy["interest_subvention_cap"]:
        interest = (
            f"Interest subvention scheme: {policy['base_interest_percent']}% a year, "
            f"effectively {policy['base_interest_percent'] - policy['prompt_repayment_benefit_percent']}% "
            "if you repay on time."
        )
    else:
        interest = (
            f"The scheme benefit applies up to Rs {policy['interest_subvention_cap']:,}; "
            "the rest is at the bank's normal rate."
        )

    return {
        "cultivation_cost": round(cultivation),
        "post_harvest_allowance": round(post_harvest),
        "maintenance_allowance": round(maintenance),
        "estimated_limit": round(total),
        "existing_loan_outstanding": round(outstanding),
        "available_limit": round(available),
        "cropped_area_acres": round(total_area * scale, 2),
        "collateral_free": total <= policy["collateral_free_limit"],
        "collateral_free_up_to": policy["collateral_free_limit"],
        "interest_note": interest,
        "crops_used": [
            {"crop": item["crop"], "area_acres": round(item["area_acres"] * scale, 2)}
            for item in crops
        ],
    }


# ------------------------------------------------------------------
# Documents
# ------------------------------------------------------------------

def missing_documents(profile, rules=None):
    rules = rules or load_rules()
    required = rules["required_documents"]

    provided = set(profile.get("documents") or [])
    ownership = ((profile.get("land") or {}).get("ownership") or "owner")

    needed = list(required["always"]) + list(required.get(ownership, required["owner"]))

    labels = required["labels"]

    return [
        {"code": code, "label": labels.get(code, code)}
        for code in needed
        if code not in provided
    ], needed


# ------------------------------------------------------------------
# Score
# ------------------------------------------------------------------

def yield_consistency(history):
    """0..1: how steady the yields of the same crop were (1 = very steady)."""

    by_crop = {}

    for item in history:
        yield_value = item.get("yield_quintal_per_acre")

        if yield_value:
            by_crop.setdefault(item["crop"].strip().lower(), []).append(float(yield_value))

    variations = []

    for values in by_crop.values():
        if len(values) >= 2 and statistics.mean(values) > 0:
            variations.append(statistics.pstdev(values) / statistics.mean(values))

    if not variations:
        return None

    return max(0.0, 1 - statistics.mean(variations) / 0.5)


def build_report(profile, weather_risk=None, rules=None):
    """
    The full eligibility report (English). Pure: no database or network,
    the weather risk is passed in.
    """

    rules = rules or load_rules()
    policy = rules["policy"]

    land = profile.get("land") or {}
    history = profile.get("crops") or []
    weather = weather_risk or _unknown_weather("Weather risk was not assessed")

    crops = planned_crops(profile)
    limit = estimate_limit(profile, crops, rules)

    missing, needed = missing_documents(profile, rules)

    blockers = []
    tips = []
    breakdown = {}

    # ---- blockers -------------------------------------------------
    if float(land.get("extent_acres") or 0) <= 0:
        blockers.append("No cultivable land is recorded. A KCC needs land you own or lease.")

    if profile.get("has_default"):
        blockers.append("A previous loan is in default. Clear the dues before applying.")

    age = profile.get("age")

    if age is not None and not (policy["min_age"] <= age <= policy["max_age"]):
        blockers.append(
            f"KCC borrowers should be {policy['min_age']}-{policy['max_age']} years old "
            "(a co-borrower can apply for older farmers)."
        )

    # ---- documents (30) ------------------------------------------
    ownership = land.get("ownership") or "owner"
    land_proof = "land_record" if ownership == "owner" else "lease_agreement"
    has_land_proof = land_proof in (profile.get("documents") or [])

    other_needed = [code for code in needed if code != land_proof]
    other_have = [code for code in other_needed if code in (profile.get("documents") or [])]

    documents_score = (
        (DOCUMENT_POINTS / 2 if has_land_proof else 0)
        + DOCUMENT_POINTS / 2 * (len(other_have) / len(other_needed) if other_needed else 1)
    )
    breakdown["documents"] = {"score": round(documents_score, 1), "max": DOCUMENT_POINTS}

    # ---- credit history (25) -------------------------------------
    if profile.get("has_default"):
        credit_score = 0.0
    else:
        burden = (
            float(profile.get("existing_loan_outstanding") or 0) / limit["estimated_limit"]
            if limit["estimated_limit"] > 0 else 0
        )
        credit_score = CREDIT_POINTS - min(10.0, burden * 10)

        if burden > 0.5:
            tips.append("Your existing loans are large compared with the limit: repay part of them first.")

    breakdown["credit_history"] = {"score": round(credit_score, 1), "max": CREDIT_POINTS}

    # ---- farming track record (20) -------------------------------
    seasons = len({(item.get("year"), item.get("season")) for item in history})
    consistency = yield_consistency(history)

    track_score = (
        TRACK_RECORD_POINTS / 2 * min(seasons, 4) / 4
        + TRACK_RECORD_POINTS / 2 * (0.5 if consistency is None else consistency)
    )
    breakdown["farming_record"] = {"score": round(track_score, 1), "max": TRACK_RECORD_POINTS}

    if seasons < 2:
        tips.append("Add your last 2-4 seasons of crops: a farming record strengthens the application.")

    # ---- soil (10) ------------------------------------------------
    soil = profile.get("soil")
    soil_assessment = assess_soil(soil, crops, rules)

    if soil_assessment is None:
        soil_score = 3.0
        tips.append("Get a Soil Health Card from your nearest Krishi Kendra: it improves the assessment.")
    else:
        soil_score = SOIL_POINTS * soil_assessment["suitability"]
        tips.extend(soil_assessment["tips"])

        if not soil_card_is_current(soil, rules):
            soil_score *= 0.7
            tips.append("Your Soil Health Card is old: renew it (it is valid for about 3 years).")

    breakdown["soil"] = {"score": round(soil_score, 1), "max": SOIL_POINTS}

    # ---- weather risk (15) ---------------------------------------
    weather_score = WEATHER_POINTS * (1 - weather["score"])
    breakdown["weather_risk"] = {"score": round(weather_score, 1), "max": WEATHER_POINTS}

    if weather["level"] == "high":
        tips.append("Your area has high weather risk: take crop insurance (PMFBY) and consider drought-tolerant crops.")

    # ---- documents tips ------------------------------------------
    if missing:
        tips.append(
            "Collect the missing documents: "
            + ", ".join(item["label"] for item in missing) + "."
        )

    if not crops:
        tips.append("Tell us which crops you plan to grow so the limit can be estimated.")

    score = round(sum(part["score"] for part in breakdown.values()))

    # ---- verdict ---------------------------------------------------
    if blockers:
        verdict_code = "not_eligible"
        verdict = "Not eligible yet"
    elif score >= ELIGIBLE_SCORE and has_land_proof:
        verdict_code = "eligible"
        verdict = "Eligible"
    else:
        verdict_code = "conditional"
        verdict = "Conditionally eligible"

    if verdict_code == "conditional" and not has_land_proof:
        tips.insert(0, "Land proof is the most important document: get your RTC/Pahani (or lease agreement).")

    return {
        "verdict_code": verdict_code,
        "verdict": verdict,
        "score": score,
        "score_breakdown": breakdown,
        "blockers": blockers,
        "estimated_limit": limit,
        "weather_risk": weather,
        "soil": soil_assessment,
        "missing_documents": missing,
        "improvement_tips": list(dict.fromkeys(tips)),          # no duplicates, keep order
        "data_sources": {
            "land": (profile.get("land_source") or "self_declared"),
            "soil": (profile.get("soil_source") or "self_declared"),
            "verified": False,
        },
        "disclaimer": DISCLAIMER,
    }


# ------------------------------------------------------------------
# Plain-language explanation
# ------------------------------------------------------------------

def template_explanation(report):
    limit = report["estimated_limit"]

    text = f"Result: {report['verdict']} (score {report['score']}/100). "

    if limit["estimated_limit"] > 0:
        text += (
            f"Estimated Kisan Credit Card limit is about Rs {limit['estimated_limit']:,}"
            + (", which can be taken without collateral" if limit["collateral_free"] else "")
            + ". "
        )

    if report["blockers"]:
        text += report["blockers"][0] + " "
    elif report["improvement_tips"]:
        text += "Next step: " + report["improvement_tips"][0]

    return text.strip()


def explain(report):
    """A short explanation for the farmer (Gemini, with a template fallback)."""

    prompt = f"""
You are a friendly bank advisor helping an Indian farmer understand a Kisan
Credit Card (KCC) eligibility check. Write 4 short, simple sentences: the
result, the estimated limit, the main reason, and the most useful next step.
Do not promise approval. Plain words, no markdown.

Result data:
{json.dumps({
    "verdict": report["verdict"],
    "score": report["score"],
    "estimated_limit": report["estimated_limit"]["estimated_limit"],
    "collateral_free": report["estimated_limit"]["collateral_free"],
    "blockers": report["blockers"],
    "missing_documents": [d["label"] for d in report["missing_documents"]],
    "tips": report["improvement_tips"][:3],
    "weather_risk": report["weather_risk"]["level"],
}, ensure_ascii=False)}
"""

    try:
        text = generate_content(prompt).text.strip()

        if text:
            return text

    except Exception as e:
        print("Loan explanation fallback:", e)

    return template_explanation(report)
