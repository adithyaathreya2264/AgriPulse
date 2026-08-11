from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.ai.assistant.chat_agent import ask_ai
from app.services.ai_session_service import (
    load_report,
    load_conversation,
    save_conversation
)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/ai-chat")
def ai_chat(request: ChatRequest, db: Session = Depends(get_db)):

    # Load latest disease report
    report = load_report(db)

    if report is None:
        return {
            "success": False,
            "message": "No disease diagnosis found. Please analyze a crop image first."
        }

    # Load previous conversation
    conversation = load_conversation(db)

    # Ask Gemini AI
    answer = ask_ai(
        report=report,
        question=request.question
    )

    # Save new conversation
    conversation.append({
        "user": request.question,
        "assistant": answer
    })

    save_conversation(
        db=db,
        conversation=conversation
    )

    return {
        "success": True,
        "answer": answer,
        "conversation": conversation
    }