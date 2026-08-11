from matplotlib.pylab import integer
from sqlalchemy import Column, Integer, String, Float
from app.models.user import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    phone= Column(String)
    image_name = Column(String)
    disease = Column(String)
    confidence = Column(Float)
    treatment = Column(String)