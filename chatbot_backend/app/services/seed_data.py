"""
Seed data: incidentes de ejemplo para la base de conocimiento.
Ejecutar con: python -m app.services.seed_data
Crea incidentes históricos que el análisis de recurrencia puede encontrar.
"""
from datetime import datetime, timezone, timedelta
from app.models.database import SessionLocal, init_db
from app.models.entities import (
    IncidentSession, ChatMessage, IncidentStatus,
    IncidentCategory, ImpactLevel, UrgencyLevel, PriorityLevel
)


SEED_INCIDENTS = [
    {
        "session_id": "hist-001",
        "user_email": "finanzas@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "Error 403 al intentar ingresar a SAP, no puedo acceder al módulo de facturación",
        "category": IncidentCategory.ERP_SAP,
        "sub_category": "Autenticación/Permisos",
        "impact": ImpactLevel.TEAM,
        "urgency": UrgencyLevel.HIGH,
        "calculated_priority": 6,
        "priority_label": PriorityLevel.ALTA,
        "service": "SAP",
        "environment": "PROD",
        "assignment_group": "Soporte SAP",
        "jira_issue_key": "IT-198",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-198",
        "ai_confidence": 0.92,
        "days_ago": 15,
    },
    {
        "session_id": "hist-002",
        "user_email": "contabilidad@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "SAP muestra error de permisos 403 al acceder a transacciones de finanzas desde esta mañana",
        "category": IncidentCategory.ERP_SAP,
        "sub_category": "Permisos SAP",
        "impact": ImpactLevel.TEAM,
        "urgency": UrgencyLevel.HIGH,
        "calculated_priority": 6,
        "priority_label": PriorityLevel.ALTA,
        "service": "SAP",
        "environment": "PROD",
        "assignment_group": "Soporte SAP",
        "jira_issue_key": "IT-210",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-210",
        "ai_confidence": 0.88,
        "days_ago": 7,
    },
    {
        "session_id": "hist-003",
        "user_email": "ventas@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "No puedo conectarme a la VPN corporativa, error de timeout, necesito acceder al CRM",
        "category": IncidentCategory.INFRAESTRUCTURA,
        "sub_category": "Conectividad VPN",
        "impact": ImpactLevel.INDIVIDUAL,
        "urgency": UrgencyLevel.MEDIUM,
        "calculated_priority": 2,
        "priority_label": PriorityLevel.BAJA,
        "service": "VPN",
        "environment": "PROD",
        "assignment_group": "Infraestructura",
        "jira_issue_key": "IT-215",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-215",
        "ai_confidence": 0.85,
        "days_ago": 5,
    },
    {
        "session_id": "hist-004",
        "user_email": "rrhh@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "Outlook no carga los correos nuevos desde ayer, ya reinicié el equipo",
        "category": IncidentCategory.SISTEMAS_MAIL,
        "sub_category": "Sincronización correo",
        "impact": ImpactLevel.INDIVIDUAL,
        "urgency": UrgencyLevel.MEDIUM,
        "calculated_priority": 2,
        "priority_label": PriorityLevel.BAJA,
        "service": "Outlook",
        "environment": "PROD",
        "assignment_group": "Soporte Mail",
        "jira_issue_key": "IT-220",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-220",
        "ai_confidence": 0.90,
        "days_ago": 3,
    },
    {
        "session_id": "hist-005",
        "user_email": "soporte@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "El servidor de base de datos principal se cayó, afecta a todos los sistemas internos",
        "category": IncidentCategory.INFRAESTRUCTURA,
        "sub_category": "Servidor/Base de datos",
        "impact": ImpactLevel.ORGANIZATION,
        "urgency": UrgencyLevel.HIGH,
        "calculated_priority": 9,
        "priority_label": PriorityLevel.CRITICA,
        "service": "Base de datos",
        "environment": "PROD",
        "assignment_group": "Infraestructura",
        "jira_issue_key": "IT-225",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-225",
        "ai_confidence": 0.95,
        "days_ago": 20,
    },
    {
        "session_id": "hist-006",
        "user_email": "legal@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "No puedo acceder al sistema de gestión documental, me pide credenciales que no reconoce",
        "category": IncidentCategory.ACCESO_IAM,
        "sub_category": "Credenciales/SSO",
        "impact": ImpactLevel.INDIVIDUAL,
        "urgency": UrgencyLevel.MEDIUM,
        "calculated_priority": 2,
        "priority_label": PriorityLevel.BAJA,
        "service": "SharePoint",
        "environment": "PROD",
        "assignment_group": "Soporte IAM",
        "jira_issue_key": "IT-230",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-230",
        "ai_confidence": 0.82,
        "days_ago": 10,
    },
    {
        "session_id": "hist-007",
        "user_email": "compras@nttdata.com",
        "status": IncidentStatus.TICKET_CREATED,
        "description": "Error al generar orden de compra en SAP, el sistema se congela al guardar",
        "category": IncidentCategory.ERP_SAP,
        "sub_category": "Módulo Compras",
        "impact": ImpactLevel.INDIVIDUAL,
        "urgency": UrgencyLevel.HIGH,
        "calculated_priority": 3,
        "priority_label": PriorityLevel.MEDIA,
        "service": "SAP",
        "environment": "PROD",
        "assignment_group": "Soporte SAP",
        "jira_issue_key": "IT-235",
        "jira_issue_url": "https://will10larl03.atlassian.net/browse/IT-235",
        "ai_confidence": 0.87,
        "days_ago": 2,
    },
]


def seed_database():
    """Inserta los incidentes de ejemplo en la base de datos."""
    init_db()
    db = SessionLocal()

    try:
        # Verificar si ya hay datos seed
        existing = db.query(IncidentSession).filter(
            IncidentSession.session_id.like("hist-%")
        ).count()

        if existing > 0:
            print(f"⚠️  Ya existen {existing} incidentes históricos, omitiendo seed.")
            return

        now = datetime.now(timezone.utc)

        for data in SEED_INCIDENTS:
            days_ago = data.pop("days_ago", 0)
            created = now - timedelta(days=days_ago)

            session = IncidentSession(
                **data,
                channel="chat",
                created_at=created,
                updated_at=created,
            )
            db.add(session)

            # Agregar un mensaje de ejemplo
            db.add(ChatMessage(
                session_id=data["session_id"],
                role="user",
                content=data["description"],
                created_at=created,
            ))
            db.add(ChatMessage(
                session_id=data["session_id"],
                role="assistant",
                content=f"Tu incidente fue registrado como {data['jira_issue_key']}.",
                created_at=created,
            ))

        db.commit()
        print(f"✅ {len(SEED_INCIDENTS)} incidentes históricos cargados exitosamente.")

    except Exception as e:
        db.rollback()
        print(f"❌ Error cargando seed data: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
