from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.db.database import get_db
from app.ai.assistant.chat_agent import ask_ai
from app.services.translation_service import (
    translate_to_english,
    translate_to_user_language
)
from app.services.ai_session_service import (
    load_report,
    load_conversation,
    save_conversation
)

router = APIRouter()


class ChatRequest(BaseModel):
    question: str
    lang: str | None = None  # en, hi, kn, te, ta, mr


@router.post("/ai-chat")
def ai_chat(request: ChatRequest, db=Depends(get_db)):

    # Load latest disease report
    report = load_report(db)

    if report is None:
        return {
            "success": False,
            "message": "No disease diagnosis found. Please analyze a crop image first."
        }

    # Load previous conversation
    conversation = load_conversation(db)

    # Understand the question in any supported language
    question, detected_lang = translate_to_english(request.question)

    # Ask Gemini AI. If every model is out of quota, answer cleanly instead of crashing (a 500
    # has no CORS headers, so the browser would only show "server not reachable").
    try:
        answer = ask_ai(
            report=report,
            question=question
        )
    except Exception as error:
        print(f"AI chat failed: {error}")

        return {
            "success": False,
            "message": (
                "The AI assistant is busy right now. "
                "Please try again in a little while."
            )
        }

    # Save the conversation in English
    conversation.append({
        "user": question,
        "assistant": answer
    })

    save_conversation(
        db=db,
        conversation=conversation
    )

    return {
        "success": True,
        "answer": translate_to_user_language(
            answer,
            request.lang or detected_lang
        ),
        "conversation": conversation
    }