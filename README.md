# AgriPulse (KisanMitra AI)

AI-assisted farming platform: crop disease diagnosis, mandi price forecasting, weather advice,
an equipment rental marketplace, a voice-first multilingual interface and a Kisan Credit Card
(KCC) eligibility advisor. *AgriPulse* and *KisanMitra AI* are the same product.

**Stack:** React (Create React App) · FastAPI · MongoDB Atlas · YOLOv8-cls / EfficientNet ·
Gemini · Sarvam AI · Razorpay (test mode) · Twilio WhatsApp.

## What is implemented

| Feature | Status | Notes |
|---|---|---|
| **Disease diagnosis** (web + WhatsApp) | Working, needs trained weights | YOLOv8-cls (`train_yolo_classifier.py`), EfficientNet-B0 fallback. Trained on PlantVillage folders, one class per folder. Replies in the farmer's language. |
| **Mandi price forecast** | Working, needs `AGMARKNET_API_KEY` | 5 years of Agmarknet history + rainfall/temperature (Open-Meteo), gradient-boosting model per horizon (7/14/21/28 days), backtested against a linear baseline, best-time-to-sell, price alerts (in-app + WhatsApp). Agmarknet has no arrivals column, so demand-supply is **not** a feature. |
| **Equipment marketplace** | Working | Login (owner / renter), GPS + 10 km search, day **and** hourly booking, drones/harvesters, owner availability toggle and location updates, Razorpay checkout with UPI first, verified payments + webhook, booking expiry and automatic Confirmed → Active → Completed. Live GPS tracker hardware is not integrated: the owner (or a device) posts the position. |
| **Voice + 14 languages** | Working (Sarvam key in `.env`) | Mic input on every page, "speak a command" navigation, spoken answers, WhatsApp voice notes in/out. Sarvam first (translation for 13 languages, speech-to-text with automatic language detection, voices for 11 languages); Gemini / browser speech as fallback. Bhojpuri is served by Gemini, and Urdu / Assamese have no Sarvam voice (the phone's own voice is used). UI labels are translated for hi, kn, te, ta, mr (hand-written, please review); other languages fall back to English until `scripts/generate_ui_translations.py` is run. |
| **Loan eligibility advisor (KCC)** | Working with **demo data** | Score, estimated limit, missing documents, tips, weather-risk score, nearby bank/CSC, printable report. The DigiLocker adapter is a **mock**; the real integration needs government partner access. Scale-of-finance values and the bank/CSC directory are **illustrative samples**. |

## Setup

```powershell
# Backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env        # then fill in the keys
python -m uvicorn app.main:app --reload --port 5556

# Frontend (second terminal)
cd kisanmitra-frontend
npm install
npm start                     # http://localhost:5555
```

FFmpeg is needed for voice (`winget install Gyan.FFmpeg`). The frontend reads
`kisanmitra-frontend/.env` (`PORT=5555`, `REACT_APP_API_URL=http://127.0.0.1:5556`).

## Configuration (`.env`)

See `.env.example`. Minimum: `MONGODB_URI`, `JWT_SECRET`. Each feature also needs its own keys
(`GEMINI_API_KEY`, `AGMARKNET_API_KEY`, `WEATHER_API_KEY`, `RAZORPAY_*`, `TWILIO_*`, `SARVAM_API_KEY`).
Missing keys switch that feature off or make it fall back; the rest of the app keeps running.

## Train the disease model

Dataset: one folder per class named `Crop___disease` (for example `Tomato___late_blight`) under
`datasets/leaf_disease_detection_dataset/` (71 classes, ~116k images; not in git).

```powershell
python scripts/prepare_dataset.py        # balanced train/val split -> datasets/prepared (report included)
python train_yolo_classifier.py          # trains yolov8n-cls, saves app/ai/models/yolov8_disease.pt
python train_yolo_classifier.py --resume # continue an interrupted run
python scripts/evaluate_model.py         # per-class accuracy, mistakes, recommended CONFIDENCE_THRESHOLD
```

Classes are capped at 500 training images so the run stays affordable on a CPU and a class with
13,000 photos does not drown one with 70. `yolov8n.pt` in the project root is a *detection*
checkpoint: its backbone is transferred into a classification model (use `--weights yolov8n-cls.pt`
for the ImageNet classification checkpoint instead). `DISEASE_MODEL=yolo` (default) uses the new
weights and falls back to `efficientnet.pth` if they are missing.

## WhatsApp bot

Farmers can send a leaf photo, a voice note, a shared location or a question. It covers disease
diagnosis with feedback, weather, mandi prices with forecasts and alerts, equipment near you, the
loan check, bookings, a daily morning message and 14 languages. Setup steps (what you have to do),
the command list and the limits are in **`docs/WHATSAPP_BOT.md`**.

## Tests

```powershell
pip install -r requirements-dev.txt
pytest                                   # backend, in-memory MongoDB, no network
cd kisanmitra-frontend; npm test -- --watchAll=false
```

`scripts/manual_check_*.py` are manual checks that call live services.

## Login (demo)

Phone + OTP with a **fake constant OTP `123456`** (no SMS is sent). New users answer a short onboarding
form (name, date of birth, state, district, language, role); it is stored in MongoDB (`users`) and comes
back when the same phone logs in again. The user id shown in the app is the first 2 + last 2 digits of
the phone number (several phones can share one; accounts are keyed by the full number).

**Anyone who knows a phone number can log in as it.** Set `FAKE_AUTH=false` to switch it off (the login
endpoints then answer 501) until a real SMS OTP provider is connected.

## Known limits

- DigiLocker (real) is not implemented. Sarvam and Gemini were checked live; Twilio and Razorpay are unit-tested with mocks and need your credentials for a live end-to-end check.
- Price forecasts are statistical estimates, not guarantees. The KCC report is advisory only.
- Rental times are server-local wall-clock time.

See `docs/REPLACE_DEMO_DATA.md` to swap the Loan Advisor's demo data for real data.
