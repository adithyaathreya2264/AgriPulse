"""
The Twilio WhatsApp webhook. The bot itself lives in app/whatsapp/.

What happens to a message:
  1. Twilio's signature is checked (nobody else can post fake messages)
  2. duplicates (Twilio retries) and message floods are dropped
  3. the bot decides what to say
  4. slow work (prices, photos, AI answers) does not have to fit into
     Twilio's 15 second limit: when Twilio credentials are set we answer
     "looking it up..." at once and send the result as a second message
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, Response
from fastapi.concurrency import run_in_threadpool
from twilio.twiml.messaging_response import MessagingResponse

from app.db.database import get_db
from app.whatsapp import bot, media, twilio_io
from app.whatsapp.localize import localize
from app.whatsapp.state import record_message
from app.whatsapp.types import Incoming, Outcome

router = APIRouter()

ERROR_TEXT = "Sorry, something went wrong. Please try again in a moment."

EMPTY = '<?xml version="1.0" encoding="UTF-8"?><Response></Response>'


def parse_form(form):
    def number(name):
        try:
            return float(form.get(name))
        except (TypeError, ValueError):
            return None

    return Incoming(
        phone=(form.get("From") or "").replace("whatsapp:", "").strip(),
        body=form.get("Body") or "",
        sid=form.get("MessageSid") or form.get("SmsMessageSid"),
        media_url=form.get("MediaUrl0") if int(form.get("NumMedia") or 0) > 0 else None,
        media_type=form.get("MediaContentType0") or "",
        latitude=number("Latitude"),
        longitude=number("Longitude"),
        profile_name=form.get("ProfileName"),
    )


def voice_url_for(outcome: Outcome, texts):
    """A voice note of the last answer, when the farmer sent a voice note."""

    if not outcome.voice or not texts:
        return None

    return media.save_voice_reply(texts[-1], outcome.lang)


def twiml(texts, media_url=None):
    response = MessagingResponse()

    parts = [part for text in texts for part in twilio_io.split_message(text)]

    for index, part in enumerate(parts):
        message = response.message(part)

        if media_url and index == len(parts) - 1:
            message.media(media_url)

    return Response(content=str(response), media_type="application/xml")


def run_deferred(db, incoming: Incoming, outcome: Outcome):
    """Background task: do the slow work, then message the farmer."""

    try:
        texts = outcome.deferred()
    except Exception as e:
        print("Bot background error:", e)
        texts = [ERROR_TEXT]

    localized = localize(db, texts, outcome.lang)

    twilio_io.send_messages(incoming.phone, localized, voice_url_for(outcome, localized))


@router.post("/whatsapp")
async def whatsapp_reply(
    request: Request,
    background: BackgroundTasks,
    db=Depends(get_db)
):
    form = await request.form()

    if not twilio_io.valid_signature(request, form):
        # no secrets here: the URL the signature was checked against, to compare with Twilio's webhook URL
        print(
            "Twilio signature rejected. Checked against URL:",
            twilio_io.public_url(request),
            "| signature header present:",
            bool(request.headers.get("X-Twilio-Signature"))
        )

        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    incoming = parse_form(form)

    if not incoming.phone:
        return Response(content=EMPTY, media_type="application/xml")

    status = record_message(db, incoming.sid, incoming.phone)

    if status == "duplicate":
        return Response(content=EMPTY, media_type="application/xml")

    try:
        outcome = await run_in_threadpool(
            bot.handle, db, incoming, status == "rate_limited"
        )

        texts = list(outcome.replies)

        if outcome.deferred:
            if twilio_io.rest_configured():
                # Answer now, send the real result when it is ready
                if outcome.ack:
                    texts.append(outcome.ack)

                background.add_task(run_deferred, db, incoming, outcome)

            else:
                texts.extend(await run_in_threadpool(outcome.deferred))

        localized = await run_in_threadpool(
            localize, db, texts, outcome.lang, outcome.static and not outcome.deferred
        )

        if outcome.prefix and localized:
            localized[0] = outcome.prefix + localized[0]

        voice = None

        if not (outcome.deferred and twilio_io.rest_configured()):
            voice = await run_in_threadpool(voice_url_for, outcome, localized)

        return twiml(localized, voice)

    except Exception as e:
        print("WhatsApp error:", e)

        return twiml([ERROR_TEXT])
