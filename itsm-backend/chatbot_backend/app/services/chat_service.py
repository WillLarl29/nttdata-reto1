"""
Orquestador principal del chat.
Conecta: DB ↔ OpenAI ↔ State Machine ↔ Jira
"""
import logging
from sqlalchemy.orm import Session as DBSession
from app.models.entities import IncidentSession, ChatMessage, IncidentStatus
from app.models.schemas import ChatRequest, ChatResponse, AIExtraction
from app.services.openai_client import extract_from_message
from app.services.jira_client import create_jira_issue
from app.services import state_machine as sm

logger = logging.getLogger(__name__)


async def process_chat_message(request: ChatRequest, db: DBSession) -> ChatResponse:
    """
    Flujo principal de cada mensaje recibido del frontend:
    
    1. Buscar o crear sesión en DB.
    2. Guardar mensaje del usuario.
    3. Construir historial y enviar a OpenAI.
    4. Aplicar extracción al borrador del incidente.
    5. Evaluar máquina de estados.
    6. Si está listo → crear ticket en Jira.
    7. Guardar respuesta del asistente en DB.
    8. Retornar response al frontend.
    """

    # ─── 1. Buscar o crear sesión ───
    session = db.query(IncidentSession).filter(
        IncidentSession.session_id == request.session_id
    ).first()

    if not session:
        session = IncidentSession(
            session_id=request.session_id,
            user_email=request.user_email,
            status=IncidentStatus.TRIAGE
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        logger.info(f"Nueva sesión creada: {request.session_id}")

    # Si la sesión ya tiene ticket, dar info de status
    if session.status in (IncidentStatus.TICKET_CREATED, IncidentStatus.CLOSED):
        reply_text = (
            f"Tu incidente ya fue registrado como {session.jira_issue_key}. "
            f"Puedes consultarlo aquí: {session.jira_issue_url}. "
            f"¿Hay algo más en lo que pueda ayudarte?"
        )
        _save_messages(db, session.session_id, request.message, reply_text)
        return ChatResponse(
            session_id=request.session_id,
            reply=reply_text,
            status=session.status.value,
            ticket_id=session.jira_issue_key,
            ticket_url=session.jira_issue_url
        )

    # ─── 2. Guardar mensaje del usuario ───
    db.add(ChatMessage(
        session_id=session.session_id,
        role="user",
        content=request.message
    ))
    db.commit()

    # ─── 3. Construir historial para OpenAI ───
    history = db.query(ChatMessage).filter(
        ChatMessage.session_id == session.session_id
    ).order_by(ChatMessage.created_at.asc()).all()

    conversation_history = [
        {"role": msg.role, "content": msg.content}
        for msg in history
    ]

    current_draft = {
        "description": session.description,
        "category": session.category.value if session.category else None,
        "impact": session.impact.value if session.impact else None,
        "urgency": session.urgency.value if session.urgency else None,
    }

    # ─── 4. Enviar a OpenAI ───
    extraction: AIExtraction = await extract_from_message(
        user_message=request.message,
        conversation_history=conversation_history,
        current_draft=current_draft
    )

    # ─── 5. Aplicar extracción al borrador ───
    if extraction.intent_type == "REPORT_INCIDENT":
        if extraction.extracted_description and not session.description:
            session.description = extraction.extracted_description

        parsed_cat = sm.try_parse_category(extraction.extracted_category)
        if parsed_cat and not session.category:
            session.category = parsed_cat

        parsed_impact = sm.try_parse_impact(extraction.extracted_impact)
        if parsed_impact and not session.impact:
            session.impact = parsed_impact

        parsed_urgency = sm.try_parse_urgency(extraction.extracted_urgency)
        if parsed_urgency and not session.urgency:
            session.urgency = parsed_urgency

    # ─── 6. Evaluar máquina de estados ───
    new_status = sm.determine_next_status(session)
    session.status = new_status
    db.commit()

    reply_text = extraction.agent_reply

    # ─── 7. Si está listo → crear ticket en Jira ───
    if new_status == IncidentStatus.READY_TO_CREATE:
        try:
            # Calcular prioridad
            priority = sm.calculate_priority(session.impact, session.urgency)
            session.calculated_priority = priority

            summary = f"[Chatbot] {session.category.value}: {session.description[:80]}"
            description_body = (
                f"*Reportado por:* {session.user_email}\n"
                f"*Categoría:* {session.category.value}\n"
                f"*Impacto:* {session.impact.value}\n"
                f"*Urgencia:* {session.urgency.value}\n"
                f"*Prioridad calculada:* {priority}/9\n\n"
                f"*Descripción del problema:*\n{session.description}"
            )

            jira_result = await create_jira_issue(
                summary=summary,
                description=description_body,
                category=session.category.value,
                priority_score=priority,
                reporter_email=session.user_email
            )

            session.jira_issue_key = jira_result["key"]
            session.jira_issue_url = jira_result["url"]
            session.status = IncidentStatus.TICKET_CREATED
            db.commit()

            reply_text = (
                f"✅ He creado tu ticket exitosamente: **{jira_result['key']}**.\n"
                f"Puedes consultarlo aquí: {jira_result['url']}\n"
                f"El equipo de soporte lo atenderá con prioridad "
                f"{'Alta' if priority >= 6 else 'Media' if priority >= 3 else 'Normal'}."
            )
            logger.info(f"Ticket creado: {jira_result['key']} para sesión {session.session_id}")

        except Exception as e:
            logger.error(f"Error creando ticket en Jira: {e}")
            reply_text = (
                "Tengo toda la información necesaria para crear tu ticket, "
                "pero estoy teniendo problemas para conectarme con Jira en este momento. "
                "Reintenataré automáticamente. Por favor espera unos segundos y escríbeme de nuevo."
            )
            # Mantener en READY_TO_CREATE para reintentar
            session.status = IncidentStatus.READY_TO_CREATE
            db.commit()

    # ─── 8. Guardar respuesta del asistente ───
    db.add(ChatMessage(
        session_id=session.session_id,
        role="assistant",
        content=reply_text
    ))
    db.commit()

    return ChatResponse(
        session_id=request.session_id,
        reply=reply_text,
        status=session.status.value,
        ticket_id=session.jira_issue_key,
        ticket_url=session.jira_issue_url
    )


def _save_messages(db: DBSession, session_id: str, user_msg: str, bot_msg: str):
    """Helper para guardar ambos mensajes de una vez."""
    db.add(ChatMessage(session_id=session_id, role="user", content=user_msg))
    db.add(ChatMessage(session_id=session_id, role="assistant", content=bot_msg))
    db.commit()
