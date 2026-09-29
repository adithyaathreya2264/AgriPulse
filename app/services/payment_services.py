import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")

if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
    raise RuntimeError("Razorpay credentials are missing from .env")

client = razorpay.Client(
    auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
)


def create_payment_order(amount, rental_id):
    """
    Create a Razorpay Test Mode order.

    Razorpay expects the amount in paise.
    Example: ₹500 = 50000 paise.
    """

    amount_paise = int(round(amount * 100))

    order_data = {
        "amount": amount_paise,
        "currency": "INR",
        "receipt": f"rental_{rental_id}",
        "notes": {
            "rental_id": str(rental_id)
        }
    }

    order = client.order.create(data=order_data)

    return order


def verify_payment(
    razorpay_order_id,
    razorpay_payment_id,
    razorpay_signature
):
    """
    Verify that the payment response came from Razorpay.
    """

    payment_data = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }

    client.utility.verify_payment_signature(payment_data)

    return True