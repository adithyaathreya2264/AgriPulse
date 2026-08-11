from sqlalchemy import Column, Integer, String
#from app.db.database import engine
from sqlalchemy.orm import declarative_base

Base=declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    phone= Column(Integer, unique=True, index=True)