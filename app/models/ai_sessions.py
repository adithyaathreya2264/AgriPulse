from sqlalchemy import Column,Integer,Text
from app.models.user import Base

class AISession(Base):
    __tablename__="ai_sessions"
    id=Column(Integer,primary_key=True,index=True)
    report=Column(Text)
    conversation=Column(Text)