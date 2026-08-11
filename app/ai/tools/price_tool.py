from app.services.price_service import predict_price
def execute(crop):
    return predict_price(crop)