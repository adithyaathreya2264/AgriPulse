from sqlalchemy import Column, Integer, String, Float, Date
from app.models.user import Base


class Rental(Base):
    __tablename__ = "rentals"

    id = Column(Integer, primary_key=True, index=True)

    equipment_id = Column(Integer, nullable=False)

    renter_name = Column(String, nullable=False)
    renter_phone = Column(String, nullable=False)

    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    total_amount = Column(Float, nullable=True)

    status = Column(String, default="Pending")

    payment_status = Column(String, default="Pending")