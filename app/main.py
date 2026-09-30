import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.db.database import get_database, init_indexes
from app.services.auth_service import fake_auth_enabled
from app.services.rental_lifecycle import lifecycle_loop, migrate_rentals
from app.services.price_alerts import price_alert_loop
from app.whatsapp.digest import digest_loop
from app.whatsapp.twilio_io import auth_token, signature_checking_enabled
from app.routes import chat_routes
from app.routes.auth_routes import router as auth_router
from app.routes.alert_routes import router as alert_router
from app.routes.voice_routes import router as voice_router
from app.routes.loan_routes import router as loan_router
from app.routes.i18n_routes import router as i18n_router
from app.routes.disease_routes import router as disease_router
from app.routes.whatsapp_routes import router as whatsapp_router
from app.routes.price_routes import router as price_router
from app.routes.weather_routes import router as weather_router
from fastapi.middleware.cors import CORSMiddleware
from app.routes.equipment_routes import router as equipment_router
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.chat_routes import router as chat_router


@asynccontextmanager
async def lifespan(app):
    # Background task: expire unpaid bookings, Confirmed -> Active -> Completed
    tasks = [
        asyncio.create_task(lifecycle_loop()),
        asyncio.create_task(price_alert_loop()),
        asyncio.create_task(digest_loop()),
    ]

    yield

    for task in tasks:
        task.cancel()


app = FastAPI(lifespan=lifespan)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in os.getenv(
            "CORS_ORIGINS", "http://localhost:5555,http://127.0.0.1:5555"
        ).split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create MongoDB indexes (does not stop the server if Atlas is unreachable)
try:
    init_indexes()
    migrate_rentals()
    print("MongoDB Atlas connected")
except Exception as e:
    print("WARNING: MongoDB is not available:", e)

# Voice replies for WhatsApp are served from here (Twilio downloads them)
os.makedirs("uploads/tts", exist_ok=True)
app.mount("/media/tts", StaticFiles(directory="uploads/tts"), name="tts")

if not signature_checking_enabled():
    print(
        "WARNING: WhatsApp webhook signature check is OFF "
        "(no TWILIO_AUTH_TOKEN, or TWILIO_VALIDATE_SIGNATURE=false): "
        "anyone can post messages to /whatsapp."
    )

if fake_auth_enabled():
    print(
        "WARNING: FAKE phone login is ON (OTP is always 123456): anyone can "
        "log in as any phone number. Set FAKE_AUTH=false before going live."
    )

# Include all routes
app.include_router(auth_router)
app.include_router(alert_router)
app.include_router(voice_router)
app.include_router(loan_router)
app.include_router(i18n_router)
app.include_router(disease_router)
app.include_router(whatsapp_router)
app.include_router(price_router)
app.include_router(weather_router)
app.include_router(dashboard_router)
app.include_router(equipment_router)
app.include_router(chat_router)
@app.get("/")
def home():
    return {"message": "KisanMitra AI backend running"}


@app.get("/health")
def health():
    try:
        get_database().command("ping")
        database = "OK"
    except Exception:
        database = "unavailable"

    return {"status": "OK", "database": database}