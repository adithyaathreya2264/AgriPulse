from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.db.database import clean, get_db, next_id
from app.services.auth_service import get_current_user
from app.services.price_alerts import check_alerts
from app.services.price_alerts import create_alert as make_alert

router = APIRouter()


class AlertRequest(BaseModel):
    crop: str = Field(min_length=1)
    district: str = Field(min_length=1)
    market: str = Field(min_length=1)
    kind: Literal["rise", "fall", "best_time"] = "best_time"
    threshold_percent: float = Field(default=5, gt=0, le=100)
    whatsapp: bool = True


@router.post("/alerts")
def create_alert(
    request: AlertRequest,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    alert = make_alert(
        db, user["id"], request.crop.strip(), request.district.strip(),
        request.market.strip(), request.kind, request.threshold_percent,
        request.whatsapp
    )

    return clean(alert)


@router.get("/alerts")
def list_alerts(user=Depends(get_current_user), db=Depends(get_db)):
    return [
        clean(alert)
        for alert in db.price_alerts.find({"user_id": user["id"]}).sort("id", -1)
    ]


@router.delete("/alerts/{alert_id}")
def delete_alert(
    alert_id: int,
    user=Depends(get_current_user),
    db=Depends(get_db)
):
    result = db.price_alerts.delete_one({"id": alert_id, "user_id": user["id"]})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Alert not found")

    return {"message": "Alert deleted"}


@router.post("/alerts/check")
def check_my_alerts(user=Depends(get_current_user), db=Depends(get_db)):
    """Run my alerts now (they also run automatically once a day)."""
    return {"notifications_created": check_alerts(db, user_id=user["id"])}


@router.get("/notifications")
def list_notifications(user=Depends(get_current_user), db=Depends(get_db)):
    return [
        clean(item)
        for item in db.notifications.find({"user_id": user["id"]})
        .sort("id", -1)
        .limit(50)
    ]


@router.post("/notifications/read-all")
def mark_all_read(user=Depends(get_current_user), db=Depends(get_db)):
    db.notifications.update_many(
        {"user_id": user["id"], "read": False},
        {"$set": {"read": True}}
    )

    return {"message": "All notifications marked as read"}
