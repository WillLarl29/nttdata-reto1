"""
Servicio de análisis de recurrencia.
Busca incidentes similares en el historial para detectar patrones
y sugerir causa raíz tentativa.
"""
import logging
from sqlalchemy.orm import Session as DBSession
from app.models.entities import IncidentSession, IncidentStatus, IncidentCategory

logger = logging.getLogger(__name__)


# Causas probables por categoría (base de conocimiento estática)
KNOWN_ROOT_CAUSES = {
    IncidentCategory.ERP_SAP: "Cambio reciente de políticas de acceso o expiración de credenciales SSO en SAP",
    IncidentCategory.ACCESO_IAM: "Bloqueo por intentos fallidos o sincronización de directorio activo",
    IncidentCategory.INFRAESTRUCTURA: "Mantenimiento no programado o degradación de capacidad en infraestructura",
    IncidentCategory.SISTEMAS_MAIL: "Problema de sincronización Exchange o certificados SMTP expirados",
    IncidentCategory.SEGURIDAD: "Posible actividad maliciosa detectada o actualización de políticas de seguridad",
    IncidentCategory.PLATAFORMA: "Actualización de plataforma con regresión o incompatibilidad",
    IncidentCategory.ERP_FINANZAS: "Cierre de periodo contable o bloqueo por conciliación pendiente",
    IncidentCategory.FACTURACION: "Error en el módulo de facturación, probablemente por configuración fiscal",
}

# Acciones preventivas por categoría
PREVENTIVE_ACTIONS = {
    IncidentCategory.ERP_SAP: "Notificar cambios de acceso con anticipación y validar expiración de credenciales periódicamente",
    IncidentCategory.ACCESO_IAM: "Implementar alertas proactivas de expiración de cuentas y revisar políticas de bloqueo",
    IncidentCategory.INFRAESTRUCTURA: "Programar ventanas de mantenimiento y monitorear capacidad con alertas tempranas",
    IncidentCategory.SISTEMAS_MAIL: "Monitorear certificados y estado de sincronización Exchange automáticamente",
    IncidentCategory.SEGURIDAD: "Realizar escaneos de seguridad periódicos y mantener endpoints actualizados",
}


def find_similar_incidents(
    db: DBSession,
    current_session: IncidentSession,
    limit: int = 5
) -> dict:
    """
    Busca incidentes similares en el historial basándose en categoría y servicio.
    
    Retorna dict con:
      - is_recurrent: bool
      - similar_tickets: list[str] (issue keys)
      - similar_details: list[dict] (info resumida)
      - probable_cause: str
      - preventive_action: str
      - recurrence_count: int
    """
    result = {
        "is_recurrent": False,
        "similar_tickets": [],
        "similar_details": [],
        "probable_cause": "-",
        "preventive_action": "-",
        "recurrence_count": 0,
    }

    if not current_session.category:
        return result

    try:
        # Buscar por misma categoría
        query = db.query(IncidentSession).filter(
            IncidentSession.category == current_session.category,
            IncidentSession.session_id != current_session.session_id,
            IncidentSession.status == IncidentStatus.TICKET_CREATED,
        )

        # Si hay servicio, priorizar mismos servicios
        if current_session.service:
            same_service = query.filter(
                IncidentSession.service == current_session.service
            ).order_by(IncidentSession.created_at.desc()).limit(limit).all()

            if same_service:
                similar = same_service
            else:
                similar = query.order_by(
                    IncidentSession.created_at.desc()
                ).limit(limit).all()
        else:
            similar = query.order_by(
                IncidentSession.created_at.desc()
            ).limit(limit).all()

        if similar:
            result["is_recurrent"] = True
            result["recurrence_count"] = len(similar)
            result["similar_tickets"] = [
                s.jira_issue_key for s in similar if s.jira_issue_key
            ]
            result["similar_details"] = [
                {
                    "ticket": s.jira_issue_key or "N/A",
                    "description": (s.description or "")[:100],
                    "service": s.service or "-",
                    "priority": s.priority_label.value if s.priority_label else "-",
                    "date": s.created_at.strftime("%Y-%m-%d") if s.created_at else "-",
                }
                for s in similar
            ]

            # Causa raíz tentativa
            result["probable_cause"] = KNOWN_ROOT_CAUSES.get(
                current_session.category,
                f"Problema recurrente en {current_session.category.value} - requiere investigación de causa raíz"
            )

            # Acción preventiva
            result["preventive_action"] = PREVENTIVE_ACTIONS.get(
                current_session.category,
                "Documentar patrón y elevar a gestión de problemas para análisis definitivo"
            )

            logger.info(
                f"Recurrencia detectada: {len(similar)} tickets similares "
                f"para categoría {current_session.category.value}"
            )

    except Exception as e:
        logger.warning(f"Error buscando recurrencias: {e}")

    return result
