# Deploying AgriPulse: backend on Render, frontend on Vercel

```
browser -> Vercel (React)  --REACT_APP_API_URL-->  Render (FastAPI, Docker)  -> MongoDB Atlas
                                                        ^
                                       Twilio WhatsApp / Razorpay webhooks
```

Deploy the **backend first** (the frontend needs its URL), then the frontend, then come back and
tell the backend the frontend's URL.

## 0. Before you push

- `.env` is git-ignored: never commit it. Secrets go into the Render dashboard.
- `app/ai/models/yolov8_disease.pt` is now allowed by `.gitignore` (3 MB). Check `git status` shows it,
  then commit and push (`Dockerfile`, `.dockerignore`, `render.yaml`, `requirements.txt` changed too).

## 1. MongoDB Atlas

Atlas -> Network Access -> **Add IP address -> Allow access from anywhere (0.0.0.0/0)**.
Render's outgoing addresses change, so a fixed allow-list will not work on the normal plans.
Keep the database user's password strong.

## 2. Backend on Render

1. render.com -> **New + -> Blueprint** -> connect the GitHub repository. It reads `render.yaml`.
   (Or **New + -> Web Service**, runtime **Docker**, health check path `/health`.)
2. **Plan:** `standard` (2 GB RAM). PyTorch + YOLO need more than the 512 MB of the free and
   starter plans; on those the disease scan crashes with "out of memory". Everything except disease
   detection would run on 512 MB. The free plan also sleeps after 15 minutes, which breaks WhatsApp
   (Twilio waits only 15 seconds for the first reply).
3. Fill the environment variables Render asks for (values from your local `.env`):

   | Variable | Value |
   |---|---|
   | `MONGODB_URI` | Atlas connection string |
   | `GEMINI_API_KEY`, `SARVAM_API_KEY`, `WEATHER_API_KEY`, `AGMARKNET_API_KEY` | your keys |
   | `RAZORPAY_KEY_ID`, `RAZORPAY_KEY_SECRET`, `RAZORPAY_WEBHOOK_SECRET` | your keys |
   | `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN` | Twilio console |
   | `CORS_ORIGINS` | the Vercel URL, e.g. `https://agripulse.vercel.app` (no trailing slash) |
   | `FRONTEND_URL` | the same Vercel URL |
   | `PUBLIC_BASE_URL` | the Render URL, e.g. `https://agripulse-api.onrender.com` |

   `CORS_ORIGINS`, `FRONTEND_URL` and `PUBLIC_BASE_URL` can be filled after step 3; save, and Render redeploys.
4. Deploy. The first Docker build takes several minutes (PyTorch). When it is live,
   `https://<your-service>.onrender.com/health` must show `{"status":"OK","database":"OK"}`.

## 3. Frontend on Vercel

1. vercel.com -> **Add New -> Project** -> import the same repository.
2. **Root Directory:** `kisanmitra-frontend`. Framework preset: Create React App (auto-detected).
   Build command `npm run build`, output `build` (defaults).
3. **Environment Variable:** `REACT_APP_API_URL` = the Render URL (no trailing slash).
   It is baked in at build time: if you change it, **redeploy**.
4. Deploy, then copy the Vercel URL into Render's `CORS_ORIGINS` and `FRONTEND_URL`.

Vercel serves HTTPS, which the microphone, GPS and camera need.

## 4. Point the outside services at Render

- **Twilio sandbox:** Messaging -> Try it out -> WhatsApp sandbox settings -> "When a message comes in":
  `https://<your-service>.onrender.com/whatsapp`, method POST. (No more ngrok.)
  `PUBLIC_BASE_URL` must be exactly that host: the signature check is computed from it.
- **Razorpay:** Dashboard -> Webhooks -> `https://<your-service>.onrender.com/razorpay-webhook`, secret = `RAZORPAY_WEBHOOK_SECRET`.
  Use test keys until you have tested a payment end to end.

## 5. Check it

1. Open the Vercel URL: the splash, then the information page.
2. Log in (demo OTP 123456), finish onboarding.
3. Weather works -> the backend and CORS are fine. Price forecast needs the Agmarknet key and network.
4. Upload a leaf photo (first scan is slow: the model loads).
5. Send "hi" to the WhatsApp sandbox number.

## Things to know

- **Demo login is public.** With `FAKE_AUTH=true` anyone who knows a phone number can log in as it
  (the OTP is always 123456). Fine for a demo; before real users, set `FAKE_AUTH=false` and add a real
  SMS OTP provider.
- **Files are temporary.** Render's disk is wiped on every deploy: WhatsApp voice replies and
  uploaded photos are short-lived by design; all real data is in Atlas.
- **Cost.** `standard` is a paid plan. Any PyTorch model needs more than 512 MB, so a cheaper plan
  only works if you accept that disease detection will fail.
- **Logs:** Render dashboard -> Logs. "MongoDB is not available" means the Atlas IP allow-list or
  `MONGODB_URI` is wrong.
- The Docker build was written but not test-built on this machine; if a package fails to install,
  the Render build log names it.
