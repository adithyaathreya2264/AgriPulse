from fastapi import APIRouter, Query

from app.services.price_service import (
    predict_price,
    search_markets
)

router = APIRouter()


@router.get("/predict-price")
def get_price(
    crop: str = Query(..., description="Name of the crop"),
    district: str = Query(None, description="Karnataka district"),
    market: str = Query(None, description="Market name")
):

    # Search markets when only crop is provided
    if not district or not market:

        markets = search_markets(crop)

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
    return predict_price(
        crop,
        district,
        market
    )