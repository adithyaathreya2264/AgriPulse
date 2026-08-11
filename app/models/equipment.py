from sqlalchemy import Column, Integer, String, Float
from app.models.user import Base

class Equipment(Base):
    __tablename__ = 'equipment'

    id = Column(Integer, primary_key=True, index=True)
    equipment_name = Column(String)
    owner_name=Column(String)
    price_per_day = Column(Float)
    location = Column(String)
    contact_number = Column(String)
    availability = Column(String, default='Available')

    #def __repr__(self):
    #    return f"<Equipment(name='{self.equipment_name}', availability='{self.availability}')>"