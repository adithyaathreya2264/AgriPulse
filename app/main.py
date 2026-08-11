from fastapi import FastAPI
from app.db.database import engine
from app.models.user import Base
from app.routes import chat_routes
from app.routes.user_routes import router as user_router
from app.routes.disease_routes import router as disease_router
from app.routes.whatsapp_routes import router as whatsapp_router
from app.routes.price_routes import router as price_router
from app.routes.weather_routes import router as weather_router
from fastapi.middleware.cors import CORSMiddleware
from app.models.equipment import Equipment
from app.routes.equipment_routes import router as equipment_router
from app.models.rental import Rental
from app.routes.dashboard_routes import router as dashboard_router
from app.routes.chat_routes import router as chat_router
app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Include all routes
app.include_router(user_router)
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
    return {"status": "OK"}