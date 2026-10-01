# Replacing the demo data of the Loan Advisor with real data

The Loan Advisor has three pieces of stand-in data. Each is isolated in one place, so swapping it
does not touch the rest of the app.

| Demo piece | Where it lives | Replace with |
|---|---|---|
| Land record + Soil Health Card | `app/services/digilocker.py` (`MockDigiLockerProvider`) | Real DigiLocker / state land-record APIs |
| Scale of finance, policy limits | `app/data/kcc_rules.json` | Official DLTC / RBI figures |
| Bank & CSC directory | `app/data/banks_csc.json` | Real branch list with coordinates |

## 1. Land record and Soil Health Card (DigiLocker)

1. Get access. These APIs are for onboarded government partners: register as a *requester* on the
   DigiLocker partner portal / API Setu (apisetu.gov.in) and ask for land-record (Karnataka: Bhoomi RTC)
   and Soil Health Card access. Requirements change, so start from their current onboarding page.
2. You receive a client id and secret. Put them in `.env`:
   ```
   DIGILOCKER_PROVIDER=real
   DIGILOCKER_CLIENT_ID=...
   DIGILOCKER_CLIENT_SECRET=...
   ```
3. Implement `RealDigiLockerProvider.fetch_land_record()` and `fetch_soil_card()` in
   `app/services/digilocker.py` (both currently raise "not implemented"). The farmer must give consent
   (OAuth) before you can read their documents.
4. Return the **same fields** the mock returns, so nothing else changes:
   - land: `survey_number, extent_acres, ownership (owner|tenant|sharecropper), irrigated, owner_name`
   - soil: `ph, oc_percent, n_kg_ha, p_kg_ha, k_kg_ha, ec_dsm, tested_on (YYYY-MM-DD)`
   - and set `"source": "digilocker"` and `"verified": True` (the mock says `mock` / `False`).
5. Unit-test it like `tests/test_loan_advisor.py` does for the mock. The button text
   "Fetch from DigiLocker (demo)" in `kisanmitra-frontend/src/LoanAdvisor.js` should lose "(demo)".

Until then the report keeps saying the data is self-declared / unverified. That is intentional.

## 2. Scale of finance and policy figures

`app/data/kcc_rules.json` holds numbers that are **illustrative**:

- `crops.<crop>.scale_of_finance` (Rs per acre): take the values for your district from the current
  District Level Technical Committee (DLTC) scale-of-finance table, published by the lead bank / SLBC
  and NABARD. One state-wide number per crop is used now; if your districts differ a lot, ask for a
  per-district override (small change in `crop_info()` in `app/services/loan_advisor.py`).
- `policy.*` (collateral-free limit, interest-subvention cap and rates, age limits): update from the
  latest RBI master direction and Government of India interest-subvention circular. Keep the
  `policy_note` text current.
- `limit_rules.*` (10% post-harvest, 20% maintenance, cropping intensity): confirm with your bank.

## 3. Bank and CSC directory

`app/data/banks_csc.json` is sample data around district headquarters. Replace `entries` with real rows:

```json
{ "type": "bank", "name": "Karnataka Grameena Bank - Kolar Main", "district": "Kolar",
  "lat": 13.1360, "lng": 78.1290 }
```

`type` is `bank` or `csc`. Sources: the SLBC Karnataka / RBI / NABARD branch lists and the CSC locator
(findmycsc.nic.in). Rows without coordinates need geocoding first (Google Maps or OpenStreetMap
Nominatim). Remove the `"sample": true` flags: the API then reports `data_source: "directory"`
instead of `"sample"`, and the on-screen "sample data" note disappears.

## Before you trust it

- Run `pytest` (limit arithmetic is tested against hand-computed values).
- Try 3-5 real cases and compare the estimated limit with what the bank actually quotes.
- Ask a bank officer or agriculture-finance expert to review the score weights in
  `build_report()`: they are this project's own design, not a bank model.
- Keep the disclaimer: the result is advisory, the bank decides.
