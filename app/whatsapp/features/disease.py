import os

from app.ai.classifier.common import ModelNotFoundError
from app.db.database import next_id
from app.services.disease_service import predict_disease
from app.services.prediction_service import save_predictions
from app.whatsapp import media
from app.whatsapp.features.common import yes_no
from app.whatsapp.state import end_flow, now_iso, set_state, update_wa_user
from app.whatsapp.types import Outcome, say

PHOTO_TIPS = (
    "For a good result: one leaf, close up and in focus, in daylight, "
    "with the sick part visible and a plain background."
)


def start(ctx):
    return say("📷 Send me a clear photo of one leaf. " + PHOTO_TIPS, static=True)


# ------------------------------------------------------------------
# Diagnosis
# ------------------------------------------------------------------

def diagnose(ctx, media_url):
    def work():
        image = media.download_media(media_url)

        if not image:
            return ["I could not download that photo. Please send it again."]

        path = media.save_photo(image)

        try:
            prediction = predict_disease(path)[0]

        except ModelNotFoundError:
            media.delete_photo(path)
            return ["Disease detection is not available right now. Please try again later."]

        except Exception as e:
            print("Diagnosis error:", e)
            media.delete_photo(path)
            return ["Sorry, I could not read that photo. Please try another one."]

        if prediction["disease"].startswith("Uncertain"):
            media.delete_photo(path)

            return [
                f"🤔 I am not sure about this photo (only {prediction['confidence']}% sure), "
                "so I will not guess. " + PHOTO_TIPS
            ]

        save_predictions(
            ctx.db,
            os.path.basename(path),
            {
                "disease": prediction["disease"],
                "confidence": prediction["confidence"],
                "medicine": prediction["treatment"],
                "model": prediction.get("model"),
            },
            phone=ctx.phone
        )

        # The assistant can talk about it, and the farmer can confirm it
        update_wa_user(ctx.db, ctx.phone, last_diagnosis={
            "disease": prediction["disease"],
            "confidence": prediction["confidence"],
            "at": now_iso(),
        })

        set_state(
            ctx, "feedback",
            path=path,
            disease=prediction["disease"],
            confidence=prediction["confidence"],
            model=prediction.get("model"),
        )

        return [
            f"🌿 {prediction['disease']}\n"
            f"Confidence: {prediction['confidence']}%\n"
            f"Treatment: {prediction['treatment']}\n\n"
            "Was I right? Reply 1 👍 yes or 2 👎 no."
        ]

    return Outcome(ack="🔍 Looking at your photo…", deferred=work)


# ------------------------------------------------------------------
# Feedback (this is how the model gets better)
# ------------------------------------------------------------------

def _save_feedback(ctx, rating, correct_label=None, keep_photo=False):
    data = ctx.data

    stored_path = None

    if keep_photo:
        stored_path = media.keep_photo_for_training(data.get("path"))
    else:
        media.delete_photo(data.get("path"))

    ctx.db.disease_feedback.insert_one({
        "id": next_id("disease_feedback"),
        "phone": ctx.phone,
        "predicted": data.get("disease"),
        "confidence": data.get("confidence"),
        "model": data.get("model"),
        "rating": rating,
        "correct_label": correct_label,
        "photo": stored_path,
        "created_at": now_iso(),
    })

    end_flow(ctx)


def on_feedback(ctx, text):
    answer = yes_no(text)

    if answer is None:
        return say("Please reply 1 👍 if I was right, or 2 👎 if not. (Or MENU.)", static=True)

    if answer:
        _save_feedback(ctx, "correct")

        return say("Thank you! 🙏 Send MENU to see what else I can do.", static=True)

    set_state(ctx, "feedback_label")

    return say(
        "Sorry about that. What is the right disease or crop? "
        "I will keep your photo to improve the model. Reply SKIP if you would rather I delete it.",
        static=True
    )


def on_label(ctx, text):
    label = " ".join(text.split())[:80]

    if label.lower() in ("skip", "no", "delete"):
        _save_feedback(ctx, "wrong")

        return say("No problem, I deleted the photo. Thank you! 🙏", static=True)

    _save_feedback(ctx, "wrong", correct_label=label, keep_photo=True)

    return say("Thank you! 🙏 This helps me learn.", static=True)
