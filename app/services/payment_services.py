import os
import razorpay
from dotenv import load_dotenv

load_dotenv()

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET")

_client = None


class PaymentConfigError(RuntimeError):
    """Razorpay credentials are missing from .env"""


def get_client():
    """
    Create the Razorpay client on first use, so the rest of the
    backend still starts when payment credentials are not configured.
    """
    global _client

    if _client is None:
        if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
            raise PaymentConfigError(
                "Razorpay credentials are missing from .env"
            )

        _client = razorpay.Client(
            auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET)
        )

    return _client


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

    return get_client().order.create(data=order_data)


def verify_payment(
    razorpay_order_id,
    razorpay_payment_id,
    razorpay_signature
):
    """
    Verify that the payment response came from Razorpay.
    Raises an error when the signature is invalid.
    """

    payment_data = {
        "razorpay_order_id": razorpay_order_id,
        "razorpay_payment_id": razorpay_payment_id,
        "razorpay_signature": razorpay_signature
    }

    get_client().utility.verify_payment_signature(payment_data)

    return True


def fetch_payment(razorpay_payment_id):
    """Ask Razorpay directly for the payment (server-side state)."""
    return get_client().payment.fetch(razorpay_payment_id)


def verify_webhook(body, signature):
    """
    Verify a Razorpay webhook. `body` is the raw request body (str).
    Raises an error when the signature is invalid.
    """

    if not RAZORPAY_WEBHOOK_SECRET:
        raise PaymentConfigError(
            "RAZORPAY_WEBHOOK_SECRET is missing from .env"
        )

    get_client().utility.verify_webhook_signature(
        body,
        signature,
        RAZORPAY_WEBHOOK_SECRET
    )

    return True
