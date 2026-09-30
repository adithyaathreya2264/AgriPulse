"""A short Kisan Credit Card check by chat (uses the same advisor as the app)."""

import re
from datetime import date

from app.services import loan_advisor
from app.whatsapp.features.common import app_link, as_number, money, yes_no
from app.whatsapp.state import end_flow, set_state
from app.whatsapp.types import Outcome, say

DOCUMENTS = {
    1: ("aadhaar", "Aadhaar card"),
    2: ("bank_passbook", "Bank passbook"),
    3: ("photo", "Passport photo"),
    4: ("land_record", "Land record (RTC / Pahani)"),
    5: ("lease_agreement", "Lease agreement"),
    6: ("soil_health_card", "Soil Health Card"),
}

OWNERSHIP = {1: "owner", 2: "tenant", 3: "sharecropper"}

VERDICT_ICON = {"eligible": "✅", "conditional": "🟡", "not_eligible": "⛔"}


# ------------------------------------------------------------------
# Questions
# ------------------------------------------------------------------

def start(ctx):
    if ctx.district:
        return _ask_acres(ctx, {"district": ctx.district})

    set_state(ctx, "loan_district", loan={})

    return say(
        "💰 Let me check your Kisan Credit Card eligibility (6 quick questions; "
        "send MENU any time to stop).\n\nFirst: which district is your farm in?",
        static=True
    )


def _ask_acres(ctx, loan):
    set_state(ctx, "loan_acres", loan=loan)

    return say(
        "💰 Kisan Credit Card check (6 quick questions; send MENU any time to stop).\n\n"
        "1/6 How many acres of land do you farm? (for example: 3 or 2.5)",
        static=True
    )


def on_district(ctx, text):
    district = " ".join(re.sub(r"[^\w\s.-]", "", text, flags=re.UNICODE).split())

    if len(district) < 2:
        return say("Please send the name of your district.", static=True)

    return _ask_acres(ctx, {"district": district.title()})


def on_acres(ctx, text):
    match = re.search(r"\d+(?:\.\d+)?", text or "")
    acres = float(match.group()) if match else 0

    if not 0 < acres <= 1000:
        return say("Please send the land size in acres as a number, for example 3 or 2.5.", static=True)

    loan = {**ctx.data["loan"], "acres": acres}
    set_state(ctx, "loan_ownership", loan=loan)

    return say(
        "2/6 Is the land yours?\n1. I own it\n2. I am a tenant (lease)\n3. I am a sharecropper",
        static=True
    )


def on_ownership(ctx, text):
    number = as_number(text)

    if number not in OWNERSHIP:
        return say("Please reply 1, 2 or 3.", static=True)

    loan = {**ctx.data["loan"], "ownership": OWNERSHIP[number]}
    set_state(ctx, "loan_crops", loan=loan)

    return say(
        "3/6 Which crops will you grow, and how many acres each?\n"
        "For example: tomato 2, ragi 1.5\n(If it is only one crop, just send its name.)",
        static=True
    )


def parse_crops(text, total_acres):
    """"tomato 2, ragi 1.5" -> [{"crop": "tomato", "area_acres": 2.0}, ...]"""

    crops = []

    for part in re.split(r",|\band\b|;|\n", text or "", flags=re.IGNORECASE):
        match = re.fullmatch(r"\s*([^\d]+?)\s*(\d+(?:\.\d+)?)?\s*(?:acres?|ac)?\s*", part.strip(), re.IGNORECASE)

        if match and match.group(1).strip():
            crop = " ".join(match.group(1).split()).lower()
            area = float(match.group(2)) if match.group(2) else None
            crops.append({"crop": crop, "area_acres": area})

    if not crops:
        return []

    missing = [item for item in crops if not item["area_acres"]]

    # Areas that were not given share what is left of the land
    if missing:
        given = sum(item["area_acres"] or 0 for item in crops)
        share = max(total_acres - given, 0) / len(missing) or total_acres / len(missing)

        for item in missing:
            item["area_acres"] = round(share, 2)

    return crops


def on_crops(ctx, text):
    crops = parse_crops(text, ctx.data["loan"]["acres"])

    if not crops:
        return say("Please send the crop names, for example: tomato 2, ragi 1.", static=True)

    loan = {**ctx.data["loan"], "crops": crops}
    set_state(ctx, "loan_outstanding", loan=loan)

    return say(
        "4/6 How much do you still owe on existing loans, in rupees? (send 0 if none)",
        static=True
    )


def on_outstanding(ctx, text):
    match = re.search(r"\d[\d,]*(?:\.\d+)?", text or "")

    if not match:
        return say("Please send the amount as a number, for example 50000 (or 0).", static=True)

    amount = float(match.group().replace(",", ""))

    loan = {**ctx.data["loan"], "outstanding": amount}
    set_state(ctx, "loan_default", loan=loan)

    return say("5/6 Is any loan of yours overdue or defaulted?\n1. Yes\n2. No", static=True)


def on_default(ctx, text):
    answer = yes_no(text)

    if answer is None:
        return say("Please reply 1 for yes or 2 for no.", static=True)

    loan = {**ctx.data["loan"], "default": answer}
    set_state(ctx, "loan_docs", loan=loan)

    menu = "\n".join(f"{number}. {label}" for number, (_, label) in DOCUMENTS.items())

    return say(
        "6/6 Which documents do you already have? Reply with the numbers, "
        f"for example: 1,2,4\n{menu}\n0. None",
        static=True
    )


def on_docs(ctx, text):
    numbers = {int(n) for n in re.findall(r"\d+", text or "")}

    if not numbers or not numbers <= set(DOCUMENTS) | {0}:
        return say("Please reply with numbers from the list, for example 1,2,4 (or 0 for none).", static=True)

    documents = [DOCUMENTS[n][0] for n in sorted(numbers) if n in DOCUMENTS]

    return report(ctx, {**ctx.data["loan"], "documents": documents})


# ------------------------------------------------------------------
# Result
# ------------------------------------------------------------------

def build_profile(ctx, loan):
    return {
        "age": ctx.account.get("age") if ctx.account else None,
        "district": loan["district"],
        "land": {
            "extent_acres": loan["acres"],
            "ownership": loan["ownership"],
        },
        "planned_crops": [
            {"crop": item["crop"], "area_acres": item["area_acres"]}
            for item in loan["crops"]
        ],
        "crops": [],
        "existing_loan_outstanding": loan["outstanding"],
        "has_default": loan["default"],
        "documents": loan["documents"],
    }


def result_text(report_data):
    limit = report_data["estimated_limit"]

    lines = [
        f"{VERDICT_ICON.get(report_data['verdict_code'], '•')} {report_data['verdict']} "
        f"(score {report_data['score']}/100)",
    ]

    if limit["estimated_limit"] > 0:
        lines.append(f"Estimated KCC limit: about {money(limit['estimated_limit'])}")

        if limit["collateral_free"]:
            lines.append(f"No collateral needed up to {money(limit['collateral_free_up_to'])}.")

        lines.append(limit["interest_note"])

    for blocker in report_data["blockers"]:
        lines.append(f"⛔ {blocker}")

    if report_data["missing_documents"]:
        lines.append("📄 Collect: " + ", ".join(d["label"] for d in report_data["missing_documents"]))

    for tip in report_data["improvement_tips"][:3]:
        lines.append(f"👉 {tip}")

    lines.append(
        f"\nAdd your past crops and soil card for a fuller report in {app_link()}. "
        "This is only an estimate — the bank decides."
    )

    return "\n".join(lines)


def report(ctx, loan):
    def work():
        profile = build_profile(ctx, loan)

        weather = loan_advisor.assess_weather_risk(loan["district"], ctx.db)
        report_data = loan_advisor.build_report(profile, weather)

        end_flow(ctx)

        return [result_text(report_data)]

    return Outcome(ack="🧮 Working it out…", deferred=work)
