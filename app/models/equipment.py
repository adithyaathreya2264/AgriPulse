from sqlalchemy import Column, Integer, String, Float, Text
from app.models.user import Base


class Equipment(Base):
    __tablename__ = "equipment"

    id = Column(Integer, primary_key=True, index=True)

    equipment_name = Column(String, nullable=False)
    category = Column(String, nullable=True)
    description = Column(Text, nullable=True)

    owner_name = Column(String, nullable=False)
    contact_number = Column(String, nullable=False)

    location = Column(String, nullable=False)
    price_per_day = Column(Float, nullable=False)

    image_url = Column(String, nullable=True)

    availability = Column(String, default="Available")