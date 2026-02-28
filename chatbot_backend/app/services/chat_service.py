"""
Orquestador principal del chat.
Conecta: DB ↔ OpenAI ↔ State Machine ↔ Jira ↔ Plantilla Enriquecida ↔ Auditoría
Actualizado para Reto 1: campos enriquecidos, fast-track, auditoría, comentario ADF.
"""
import json
import logging
from datetime import datetime, timezone
from sqlalchemy.orm import Session as DBSession
from app.models.entities import (
    IncidentSession, ChatMessage, AIDecisionLog,
    IncidentStatus, ImpactLevel, UrgencyLevel
)
from app.models.schemas import ChatRequest, ChatResponse, AIExtraction
from app.services.openai_client import extract_from_message
from app.services.jira_client import create_jira_issue, add_comment
from app.services import state_machine as sm
from app.services.incident_template import (
    render_incident_template_pro, build_enrichment_from_session
)
from app.services.recurrence_service import find_similar_incidents

logger = logging.getLogger(__name__)


async def process_chat_message(request: ChatRequest, db: DBSession) -> ChatResponse:
    """
    Flujo principal de cada mensaje recibido del frontend:
    
    1. Buscar o crear sesión en DB.
    2. Guardar mensaje del usuario.
    3. Construir historial y enviar a OpenAI.
    4. Aplicar extracción enriquecida al borrador del incidente.
    5. Evaluar máquina de estados (con fast-track si es crítico).
    6. Si está listo → crear ticket en Jira + comentario enriquecido.
    7. Guardar AIDecisionLog para auditoría.
    8. Guardar respuesta del asistente en DB.
    9. Retornar response al frontend.
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
        "sub_category": session.sub_category,
        "impact": session.impact.value if session.impact else None,
        "urgency": session.urgency.value if session.urgency else None,
        "service": session.service,
        "environment": session.environment,
    }

    # ─── 4. Enviar a OpenAI ───
    extraction: AIExtraction = await extract_from_message(
        user_message=request.message,
        conversation_history=conversation_history,
        current_draft=current_draft
    )

    # ─── 5. Aplicar extracción enriquecida al borrador ───
    is_fast_track = False
    if extraction.intent_type == "REPORT_INCIDENT":
        # Campos básicos
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

        # Campos enriquecidos (Reto 1)
        if extraction.extracted_sub_category and not session.sub_category:
            session.sub_category = extraction.extracted_sub_category

        if extraction.extracted_service and not session.service:
            session.service = extraction.extracted_service

        if extraction.extracted_environment and not session.environment:
            session.environment = extraction.extracted_environment

        if extraction.extracted_assignment_group and not session.assignment_group:
            session.assignment_group = extraction.extracted_assignment_group

        # Trazabilidad
        if extraction.confidence is not None:
            session.ai_confidence = extraction.confidence

        ai_reasoning = {
            "evidence_snippets": extraction.evidence_snippets,
            "assumptions": extraction.assumptions,
            "rules_used": extraction.rules_used,
        }
        session.ai_reasoning = json.dumps(ai_reasoning, ensure_ascii=False)

        # Fast-track: incidente crítico
        if extraction.is_critical:
            is_fast_track = True
            # Asumir máximos si no están definidos
            if not session.impact:
                session.impact = ImpactLevel.ORGANIZATION
            if not session.urgency:
                session.urgency = UrgencyLevel.HIGH
            logger.info(f"🚨 Fast-track activado para sesión {session.session_id}")

    # ─── 6. Evaluar máquina de estados ───
    new_status = sm.determine_next_status(session, fast_track=is_fast_track)
    session.status = new_status
    db.commit()

    reply_text = extraction.agent_reply

    # ─── 7. Si está listo → crear ticket en Jira + comentario enriquecido ───
    if new_status == IncidentStatus.READY_TO_CREATE:
        try:
            # Calcular prioridad
            priority = sm.calculate_priority(session.impact, session.urgency)
            session.calculated_priority = priority
            session.priority_label = sm.priority_score_to_label(priority)

            # Análisis de recurrencia
            recurrence = find_similar_incidents(db, session)

            priority_name = session.priority_label.value if session.priority_label else "Media"
            summary = f"[Chatbot] {session.category.value}: {session.description[:80]}"

            # Construir descripción enriquecida con recurrencia
            description_body = (
                f"*Reportado por:* {session.user_email}\n"
                f"*Categoría:* {session.category.value}\n"
                f"*Subcategoría:* {session.sub_category or '-'}\n"
                f"*Servicio:* {session.service or '-'}\n"
                f"*Ambiente:* {session.environment or '-'}\n"
                f"*Impacto:* {session.impact.value}\n"
                f"*Urgencia:* {session.urgency.value}\n"
                f"*Prioridad:* {priority_name} ({priority}/9)\n\n"
                f"*Descripción del problema:*\n{session.description}"
            )
            if recurrence["is_recurrent"]:
                tickets_str = ", ".join(recurrence["similar_tickets"])
                description_body += (
                    f"\n\n---\n*⚠️ INCIDENTE RECURRENTE*\n"
                    f"*Tickets similares:* {tickets_str}\n"
                    f"*Causa probable:* {recurrence['probable_cause']}\n"
                    f"*Acción preventiva:* {recurrence['preventive_action']}"
                )

            # Labels extra
            extra_labels = [f"p_{priority_name.lower()}"]
            if is_fast_track:
                extra_labels.append("fast_track")
            if recurrence["is_recurrent"]:
                extra_labels.append("recurrente")

            jira_result = await create_jira_issue(
                summary=summary,
                description=description_body,
                category=session.category.value,
                priority_score=priority,
                reporter_email=session.user_email,
                extra_labels=extra_labels
            )

            session.jira_issue_key = jira_result["key"]
            session.jira_issue_url = jira_result["url"]
            session.status = IncidentStatus.TICKET_CREATED
            db.commit()

            # Agregar comentario enriquecido con plantilla del Reto 1
            try:
                issue_data = {
                    "issue_key": jira_result["key"],
                    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    "reporter_email": session.user_email,
                    "channel": session.channel or "chat",
                    "summary": summary,
                    "description": session.description,
                }
                enrichment = build_enrichment_from_session(session, extraction)
                # Agregar datos de recurrencia al enrichment
                enrichment["analytics"] = {
                    "is_recurrent": recurrence["is_recurrent"],
                    "similar_tickets": recurrence["similar_tickets"],
                    "probable_cause": recurrence["probable_cause"],
                    "preventive_action": recurrence["preventive_action"],
                }
                template_text = render_incident_template_pro(issue_data, enrichment)
                await add_comment(jira_result["key"], template_text)
            except Exception as tmpl_err:
                logger.warning(f"No se pudo agregar plantilla enriquecida: {tmpl_err}")

            # Construir respuesta al usuario con info de recurrencia
            reply_text = (
                f"✅ He creado tu ticket exitosamente: **{jira_result['key']}**.\n"
                f"Puedes consultarlo aquí: {jira_result['url']}\n"
                f"Prioridad asignada: **{priority_name}**."
            )
            if recurrence["is_recurrent"]:
                tickets_str = ", ".join(recurrence["similar_tickets"])
                reply_text += (
                    f"\n\n⚠️ *Incidente recurrente detectado.* "
                    f"Se encontraron {recurrence['recurrence_count']} tickets similares: {tickets_str}.\n"
                    f"Causa probable: {recurrence['probable_cause']}"
                )
            else:
                reply_text += " El equipo de soporte lo atenderá según corresponda."

            logger.info(f"Ticket creado: {jira_result['key']} para sesión {session.session_id}")

        except Exception as e:
            logger.error(f"Error creando ticket en Jira: {e}")
            reply_text = (
                "Tengo toda la información necesaria para crear tu ticket, "
                "pero estoy teniendo problemas para conectarme con Jira en este momento. "
                "Reintentaré automáticamente. Por favor espera unos segundos y escríbeme de nuevo."
            )
            # Mantener en READY_TO_CREATE para reintentar
            session.status = IncidentStatus.READY_TO_CREATE
            db.commit()

    # ─── 8. Guardar AIDecisionLog para auditoría ───
    if extraction.intent_type == "REPORT_INCIDENT":
        try:
            decision = AIDecisionLog(
                session_id=session.session_id,
                step_name="classification_and_enrichment",
                input_data=json.dumps({
                    "user_message": request.message,
                    "current_draft": current_draft,
                }, ensure_ascii=False),
                output_data=json.dumps(extraction.model_dump(), ensure_ascii=False, default=str),
                confidence=extraction.confidence,
            )
            db.add(decision)
            db.commit()
        except Exception as audit_err:
            logger.warning(f"No se pudo guardar AIDecisionLog: {audit_err}")

    # ─── 9. Guardar respuesta del asistente ───
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
