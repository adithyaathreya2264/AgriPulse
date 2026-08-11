from urllib import response

from fastapi import APIRouter, Request, Response, Depends
from twilio.twiml.messaging_response import MessagingResponse
import requests
from requests.auth import HTTPBasicAuth
import os
from sqlalchemy.orm import Session

from app.services.disease_service import predict_disease
from app.services.prediction_service import save_predictions
from app.services.voice_service import convert_ogg_to_wav, speech_to_text
from app.services.translation_service import translate_to_english
from app.db.database import SessionLocal
from app.services.price_service import predict_price
from app.routes.weather_routes import get_weather

router = APIRouter()

UPLOAD_DIR = "uploads"

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 🔥 Robust media download function
def download_media(media_url):
    try:
        print("Media URL:", media_url)

        # Try with auth
        response = requests.get(
            media_url,
            auth=HTTPBasicAuth(ACCOUNT_SID, AUTH_TOKEN),
            headers={"User-Agent": "Mozilla/5.0"},
            stream=True
        )

        if response.status_code == 200:
            return response.content

        print("Auth failed, trying without auth...")

        # Try without auth
        response = requests.get(
            media_url,
            headers={"User-Agent": "Mozilla/5.0"},
            stream=True
        )

        if response.status_code == 200:
            return response.content

        print("Download failed. Status:", response.status_code)
        return None

    except Exception as e:
        print("Download error:", e)
        return None


@router.post("/whatsapp")
async def whatsapp_reply(request: Request, db: Session = Depends(get_db)):
    try:
        form = await request.form()
        num_media = int(form.get("NumMedia", 0))
        response = MessagingResponse()

        # =========================
        # MEDIA (IMAGE / AUDIO)
        # =========================
        if num_media > 0:
            media_url = form.get("MediaUrl0")
            content_type = form.get("MediaContentType0", "")

            media_content = download_media(media_url)

            if not media_content:
                response.message("Failed to download media.")
                return Response(str(response), media_type="application/xml")

            # VOICE
            if "audio" in content_type:
                ogg_path = os.path.join(UPLOAD_DIR, "voice.ogg")
                wav_path = os.path.join(UPLOAD_DIR, "voice.wav")

                with open(ogg_path, "wb") as f:
                    f.write(media_content)

                convert_ogg_to_wav(ogg_path, wav_path)
                text = speech_to_text(wav_path)

                translated = translate_to_english(text)

                response.message(f"You said (voice): {translated}")

            # 📸 IMAGE
            elif "image" in content_type:
                image_path = os.path.join(UPLOAD_DIR, "image.jpg")

                with open(image_path, "wb") as f:
                    f.write(media_content)

                predictions = predict_disease(image_path)
                save_predictions(db, "image.jpg", predictions, phone=form.get("From").replace("whatsapp:", ""))

                if predictions:
                    result = predictions[0]
                    message = (
                        f"Disease: {result['disease']}\n"
                        f"Confidence: {result['confidence']}\n"
                        f"Treatment: {result['treatment']}"
                    )
                else:
                    message = "⚠️ Something went wrong. Please try again."

                response.message(message)

            else:
                response.message("Unsupported media type.")

        # =========================
        # TEXT
        # =========================
        else:
            incoming_msg = form.get("Body", "")
            translated = translate_to_english(incoming_msg).lower()
            
            #price command
            if translated.startswith("price"):
                try:
                    parts=translated.split()
                    crop=parts[1]
                    result=predict_price(crop)
                    if "error" in result:
                        message="Crop not found"
                    else:
                        message=(
                            f"Crop: {result['crop']}\n"
                            f"Month: {result['month']}\n"
                            f"Predicted Price: {result['predicted_price']}"
                        )
                except:
                    message="⚠️ Use formate: price <crop>"
                response.message(message)

            elif translated.startswith("weather"):
                try:
                    parts=translated.split()
                    city=parts[1]
                    result=get_weather(city)
                    if "error" in result:
                        message="City not found"
                    else:
                        message=(
                            f"City: {result['city']}\n"
                            f"Temperature: {result['temperature']}°C\n"
                            f"Condition: {result['condition']}\n"
                            f"Advice: {result['advice']}"
                        )
                except:
                    message="⚠️ Use format: weather <city>"
                response.message(message)    
            else:
                response.message(f"Processed: {translated}")
            
        return Response(content=str(response), media_type="application/xml")

    except Exception as e:
        print("ERROR:", e)
        response = MessagingResponse()
        response.message(f"Error: {str(e)}")
        return Response(content=str(response), media_type="application/xml")