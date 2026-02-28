from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession
from app.models.schemas import (
    ChatRequest, ChatResponse,
    IncidentDetail, IncidentListResponse, IncidentSummary, AIDecisionLogResponse
)
from app.models.database import get_db
from app.models.entities import IncidentSession, AIDecisionLog
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


@router.get("/incidents/{session_id}", response_model=IncidentDetail)
async def get_incident(session_id: str, db: DBSession = Depends(get_db)):
    """
    Obtiene el detalle completo de un incidente con su traza de decisiones IA.
    Incluye toda la información enriquecida y los logs de auditoría.
    """
    session = db.query(IncidentSession).filter(
        IncidentSession.session_id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Incidente no encontrado")

    # Obtener logs de decisiones
    decisions = db.query(AIDecisionLog).filter(
        AIDecisionLog.session_id == session_id
    ).order_by(AIDecisionLog.created_at.asc()).all()

    decision_responses = [
        AIDecisionLogResponse(
            step_name=d.step_name,
            confidence=d.confidence,
            output_data=d.output_data,
            created_at=d.created_at,
        )
        for d in decisions
    ]

    return IncidentDetail(
        session_id=session.session_id,
        user_email=session.user_email,
        status=session.status.value,
        description=session.description,
        category=session.category.value if session.category else None,
        sub_category=session.sub_category,
        impact=session.impact.value if session.impact else None,
        urgency=session.urgency.value if session.urgency else None,
        priority_label=session.priority_label.value if session.priority_label else None,
        calculated_priority=session.calculated_priority,
        service=session.service,
        environment=session.environment,
        assignment_group=session.assignment_group,
        ai_confidence=session.ai_confidence,
        jira_issue_key=session.jira_issue_key,
        jira_issue_url=session.jira_issue_url,
        created_at=session.created_at,
        decisions=decision_responses,
    )


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    status: str | None = Query(None, description="Filtrar por estado (TRIAGE, PENDING_INFO, etc.)"),
    category: str | None = Query(None, description="Filtrar por categoría ITSM"),
    limit: int = Query(50, ge=1, le=200, description="Máximo de resultados"),
    db: DBSession = Depends(get_db)
):
    """
    Lista incidentes recientes con filtros opcionales.
    Útil para dashboards y monitoreo de tickets.
    """
    query = db.query(IncidentSession)

    if status:
        query = query.filter(IncidentSession.status == status)
    if category:
        query = query.filter(IncidentSession.category == category)

    sessions = query.order_by(IncidentSession.created_at.desc()).limit(limit).all()

    summaries = [
        IncidentSummary(
            session_id=s.session_id,
            user_email=s.user_email,
            status=s.status.value,
            category=s.category.value if s.category else None,
            priority_label=s.priority_label.value if s.priority_label else None,
            jira_issue_key=s.jira_issue_key,
            created_at=s.created_at,
        )
        for s in sessions
    ]

    return IncidentListResponse(
        total=len(summaries),
        incidents=summaries,
    )
