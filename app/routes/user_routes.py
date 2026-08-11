from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.user import User

router = APIRouter()

#db dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/users")
def create_user(name: str, phone: int, db: Session = Depends(get_db)):
    user = User(name=name, phone=phone)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router.get("/users")
def get_users(db: Session = Depends(get_db)):
    return db.query(User).all()
    