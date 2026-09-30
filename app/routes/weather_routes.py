from fastapi import APIRouter, Query
from app.services.weather_service import get_weather
from app.services.translation_service import translate_payload

router=APIRouter()
@router.get("/weather")
def weather(
    city: str = Query(...),
    lang: str = Query("en", description="en, hi, kn, te, ta, mr")
):
    return translate_payload(get_weather(city), lang)