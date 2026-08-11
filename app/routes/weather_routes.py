from fastapi import APIRouter, Query
from app.services.weather_service import get_weather

router=APIRouter()
@router.get("/weather")
def weather(city: str = Query(...)):
    return get_weather(city)