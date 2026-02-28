from pydantic import BaseModel


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
#  MODELO DE EXTRACCIÓN QUE OPENAI DEBE DEVOLVER
#  (Structured Outputs / JSON Schema)
# ──────────────────────────────────────────────

class AIExtraction(BaseModel):
    """
    Esquema que forzamos a GPT a devolver.
    El backend usa estos campos para llenar el borrador del incidente.
    """
    intent_type: str
    """Tipo de intención detectada: REPORT_INCIDENT, ASK_STATUS, GENERAL_CHAT"""

    extracted_description: str | None = None
    """Resumen breve del problema extraído del mensaje del usuario."""

    extracted_category: str | None = None
    """Categoría detectada: HARDWARE, SOFTWARE, RED, ACCESOS, OTROS"""

    extracted_impact: str | None = None
    """Impacto detectado: INDIVIDUAL, EQUIPO, ORGANIZACION"""

    extracted_urgency: str | None = None
    """Urgencia detectada: BAJA, MEDIA, ALTA"""

    missing_fields: list[str] = []
    """Lista de campos que aún faltan por recolectar, ej: ['impact', 'category']"""

    agent_reply: str
    """Texto amigable que el bot le dará al usuario como respuesta."""
