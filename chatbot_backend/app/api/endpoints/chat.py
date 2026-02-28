from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from app.models.schemas import ChatRequest, ChatResponse
from app.models.database import get_db
from app.services.chat_service import process_chat_message

router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat_interaction(request: ChatRequest, db: DBSession = Depends(get_db)):
    """
    Endpoint principal del chatbot de incidentes.
    Recibe un mensaje del usuario y devuelve la respuesta del asistente.
    La lógica real vive en chat_service.process_chat_message.
    """
    response = await process_chat_message(request, db)
    return response
