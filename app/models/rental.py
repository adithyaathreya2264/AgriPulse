from sqlalchemy import Column, Integer, String
from app.models.user import Base

class Rental(Base):
    __tablename__ = 'rentals'

    id = Column(Integer, primary_key=True, index=True)
    #user_id = Column(Integer)
    equipment_id = Column(Integer)
    renter_name = Column(String)
    renter_phone = Column(String)
    status=Column(String, default='Pending')