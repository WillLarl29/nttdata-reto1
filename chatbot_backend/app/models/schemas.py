from pydantic import BaseModel
from datetime import datetime


# ──────────────────────────────────────────────
#  REQUEST / RESPONSE del Endpoint /chat
# ──────────────────────────────────────────────

class ChatRequest(BaseModel):
    session_id: str
    user_email: str
    message: str


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    status: str
    ticket_id: str | None = None
    ticket_url: str | None = None


# ──────────────────────────────────────────────
#  MODELO DE EXTRACCIÓN ENRIQUECIDA (OpenAI)
#  Alineado con Reto 1: clasificación, priorización,
#  explicabilidad, soporte, y fast-track
# ──────────────────────────────────────────────

class AIExtraction(BaseModel):
    """
    Esquema que forzamos a GPT a devolver.
    El backend usa estos campos para llenar el borrador del incidente.
    """
    intent_type: str
    """Tipo de intención detectada: REPORT_INCIDENT, ASK_STATUS, GENERAL_CHAT"""

    # Clasificación
    extracted_description: str | None = None
    """Resumen breve del problema extraído del mensaje del usuario."""

    extracted_category: str | None = None
    """Categoría ITSM detectada (ej: 'ERP / SAP', 'Acceso / IAM')."""

    extracted_sub_category: str | None = None
    """Subcategoría más específica (ej: 'Autenticación/Permisos')."""

    extracted_impact: str | None = None
    """Impacto detectado: INDIVIDUAL, EQUIPO, ORGANIZACION"""

    extracted_urgency: str | None = None
    """Urgencia detectada: BAJA, MEDIA, ALTA"""

    # Campos enriquecidos – Reto 1
    extracted_service: str | None = None
    """Sistema o servicio afectado (ej: 'SAP', 'VPN', 'Outlook')."""

    extracted_environment: str | None = None
    """Ambiente: PROD, QA, DEV."""

    extracted_assignment_group: str | None = None
    """Grupo de soporte sugerido (ej: 'Soporte SAP', 'Infraestructura')."""

    # Explicabilidad / Trazabilidad
    confidence: float | None = None
    """Confianza del modelo en la clasificación (0.0 - 1.0)."""

    evidence_snippets: list[str] = []
    """Fragmentos del texto que justifican la clasificación."""

    assumptions: list[str] = []
    """Supuestos hechos por la IA al clasificar."""

    rules_used: list[str] = []
    """Reglas o patrones aplicados por la IA."""

    # Fast-track
    is_critical: bool = False
    """True si el incidente es crítico y debe usar fast-track."""

    # Campos faltantes y respuesta
    missing_fields: list[str] = []
    """Lista de campos que aún faltan por recolectar, ej: ['impact', 'category']"""

    agent_reply: str
    """Texto amigable que el bot le dará al usuario como respuesta."""


# ──────────────────────────────────────────────
#  SCHEMAS PARA ENDPOINTS DE CONSULTA
# ──────────────────────────────────────────────

class AIDecisionLogResponse(BaseModel):
    step_name: str
    confidence: float | None = None
    output_data: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class IncidentDetail(BaseModel):
    """Detalle completo de un incidente con su traza de decisiones."""
    session_id: str
    user_email: str
    status: str
    description: str | None = None
    category: str | None = None
    sub_category: str | None = None
    impact: str | None = None
    urgency: str | None = None
    priority_label: str | None = None
    calculated_priority: int | None = None
    service: str | None = None
    environment: str | None = None
    assignment_group: str | None = None
    ai_confidence: float | None = None
    jira_issue_key: str | None = None
    jira_issue_url: str | None = None
    created_at: datetime | None = None
    decisions: list[AIDecisionLogResponse] = []

    model_config = {"from_attributes": True}


class IncidentSummary(BaseModel):
    """Resumen corto para el listado de incidentes."""
    session_id: str
    user_email: str
    status: str
    category: str | None = None
    priority_label: str | None = None
    jira_issue_key: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class IncidentListResponse(BaseModel):
    total: int
    incidents: list[IncidentSummary]
