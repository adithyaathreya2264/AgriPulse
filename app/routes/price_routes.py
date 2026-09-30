from fastapi import APIRouter, Query

from app.services.translation_service import translate_payload
from app.services.price_service import (
    MarketDataUnavailable,
    predict_price,
    search_markets
)

router = APIRouter()


@router.get("/predict-price")
def get_price(
    crop: str = Query(..., description="Name of the crop"),
    district: str = Query(None, description="Karnataka district"),
    market: str = Query(None, description="Market name"),
    lang: str = Query("en", description="en, hi, kn, te, ta, mr")
):

    # Search markets when only crop is provided
    if not district or not market:

        try:
            markets = search_markets(crop)
        except MarketDataUnavailable as e:
            return {
                "crop": crop,
                "error": str(e) + ". Please try again later."
            }

        if not markets:
            return {
                "crop": crop,
                "error": "No Karnataka markets found for this crop"
            }

        return {
            "crop": crop,
            "markets": markets
        }

    # Price prediction when district and market are selected
    return translate_payload(
        predict_price(
            crop,
            district,
            market
        ),
        lang
    )