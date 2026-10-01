# AgriPulse WhatsApp bot

The bot answers farmers on WhatsApp through Twilio. Everything runs in your FastAPI backend
(`POST /whatsapp`); Twilio only carries the messages.

```
phone -> WhatsApp -> Twilio -> ngrok / your server -> /whatsapp -> the bot -> reply
```

## What farmers can do

| Send | The bot |
|---|---|
| a leaf photo | Diagnoses the disease, gives treatment, asks "Was I right? 👍 👎". A 👎 plus the right name keeps the photo for retraining; a 👍 deletes it. Unsure photos get retake tips instead of a guess. |
| `weather Mysuru` (or "tell me the weather in Mysuru") | Weather and farming advice. Without a city it uses the district on the farmer's account. |
| `price tomato` | Lists markets, then the farmer replies with a number for the 4-week forecast and best time to sell. `price tomato, Kolar, Kolar` skips the list. |
| `ALERT` (after a forecast) | Price alerts for that market. `alerts` lists them, `stop alert 1` removes one. Needs an account. |
| a shared location 📎 | Equipment for rent within 10 km: price, distance, owner phone, "live" if its GPS is reporting. |
| a voice note | Understood in any supported language (Sarvam), answered in text and as a voice note. |
| any farming question | Answered by Gemini, in the farmer's language, using their district and latest diagnosis. |
| `loan` | Six questions, then a Kisan Credit Card estimate (verdict, limit, tips). |
| `bookings` | Their equipment bookings (renting or renting out). Needs an account. |
| `digest on` / `digest off` | A morning weather message with a farming tip at 7:00 (`DIGEST_HOUR`). |
| `language kannada` (or `language`, then a number) | Changes the bot's language (14 languages). |
| `menu`, `cancel`, `STOP`, `START` | Menu, leave a question, stop / restart alerts and morning messages. |

"Needs an account": the farmer registered in the web app with **the same phone number**.
Their district and language are then used automatically.

## What you have to do

1. **Twilio account and sandbox** (free): twilio.com -> Messaging -> Try it out -> Send a WhatsApp
   message. Send the `join <words>` message from your phone to the sandbox number.
2. **Put the keys in `.env`** (never commit them):
   ```
   TWILIO_ACCOUNT_SID=AC...
   TWILIO_AUTH_TOKEN=...
   TWILIO_WHATSAPP_FROM=whatsapp:+14155238886      # the sandbox number Twilio shows
   ```
3. **Start the backend** on port 5556, then a tunnel: `ngrok http 5556`.
4. **Put the tunnel address in `.env`** and restart the backend:
   ```
   PUBLIC_BASE_URL=https://<your-subdomain>.ngrok-free.app
   ```
   This must be the exact address Twilio calls: the signature check is computed from it.
5. **Tell Twilio where the bot is:** Sandbox settings -> "When a message comes in" ->
   `https://<your-subdomain>.ngrok-free.app/whatsapp`, method **POST**. Save.
6. **Try it:** send `hi`, `weather Mysuru`, a leaf photo, a voice note.

The free ngrok address changes every time ngrok restarts: repeat steps 4 and 5 then.

### Also useful
- `FRONTEND_URL=https://...` : the link shown to farmers who need to register.
- `DIGEST_HOUR=7` : hour of the morning message (server time).
- For a chat test without Twilio: `curl.exe -X POST http://127.0.0.1:5556/whatsapp -d "From=whatsapp:+919999999999" -d "Body=weather Mysuru" -d "NumMedia=0"`
  (works while `TWILIO_AUTH_TOKEN` is empty, or with `TWILIO_VALIDATE_SIGNATURE=false`).

## How it is protected

- **Signature check:** with `TWILIO_AUTH_TOKEN` set, every request must carry Twilio's signature or it
  gets `403`. Nobody else can post fake messages. If every message gets 403 in the ngrok inspector
  (`http://127.0.0.1:4040`), `PUBLIC_BASE_URL` does not match the address Twilio calls.
- **Duplicates:** Twilio retries; a message is answered once (by `MessageSid`).
- **Flood limit:** more than 30 messages in 10 minutes from one phone gets a "please wait" answer
  (protects your Gemini / Sarvam quota).
- **Privacy:** photos are deleted after the diagnosis unless the farmer corrects it; the first message
  explains this. `STOP` turns off alerts and morning messages.
- **Twilio's 15 second limit:** prices, photos and AI answers take longer. With the Twilio keys set the
  bot replies "Looking it up..." at once and sends the real answer as a second message.

## Limits to know

- **Sandbox:** only phones that joined can use it, the join lasts a few days, and you can only message
  a farmer within 24 hours of their last message. That also limits the morning digest and price alerts.
  A real WhatsApp business number (via Twilio or Meta) with approved templates removes this.
- The price service (`api.data.gov.in`) must be reachable from the server. If it is not, the bot says so.
- Answers from the assistant are advice, not a substitute for the local agriculture officer.

## Code map

`app/routes/whatsapp_routes.py` (webhook) -> `app/whatsapp/bot.py` (understands the message) ->
`app/whatsapp/features/*.py` (one file per feature). Conversation memory: `state.py`. Twilio:
`twilio_io.py`. Photos and voice: `media.py`. Morning message: `digest.py`. Tests: `tests/test_whatsapp_bot.py`.
