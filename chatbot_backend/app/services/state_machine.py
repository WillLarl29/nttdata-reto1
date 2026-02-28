"""
Máquina de estados del incidente.
Decide transiciones y calcula prioridad basándose en los campos
recolectados progresivamente.
Actualizado para Reto 1: categorías ITSM, fast-track, PriorityLevel.
"""
from app.models.entities import (
    IncidentStatus, IncidentCategory, ImpactLevel, UrgencyLevel, PriorityLevel
)


# Campos obligatorios para poder crear un ticket en Jira (modo normal)
REQUIRED_FIELDS = ["description", "category", "impact", "urgency"]

# Campos obligatorios en fast-track (incidente crítico)
REQUIRED_FIELDS_FAST_TRACK = ["description", "category"]

# Mapeo de enums a valores numéricos para el cálculo de prioridad
IMPACT_VALUES = {
    ImpactLevel.INDIVIDUAL: 1,
    ImpactLevel.TEAM: 2,
    ImpactLevel.ORGANIZATION: 3,
}

URGENCY_VALUES = {
    UrgencyLevel.LOW: 1,
    UrgencyLevel.MEDIUM: 2,
    UrgencyLevel.HIGH: 3,
}


def get_missing_fields(session, fast_track: bool = False) -> list[str]:
    """
    Revisa qué campos obligatorios del borrador aún están vacíos.
    En fast-track, solo se requieren description y category.
    """
    required = REQUIRED_FIELDS_FAST_TRACK if fast_track else REQUIRED_FIELDS
    missing = []
    if "description" in required and not session.description:
        missing.append("description")
    if "category" in required and not session.category:
        missing.append("category")
    if "impact" in required and not session.impact:
        missing.append("impact")
    if "urgency" in required and not session.urgency:
        missing.append("urgency")
    return missing


def calculate_priority(impact: ImpactLevel, urgency: UrgencyLevel) -> int:
    """
    Calcula prioridad como Impacto × Urgencia.
    Resultado: 1 (mínima) a 9 (máxima/crítica).
    """
    return IMPACT_VALUES.get(impact, 1) * URGENCY_VALUES.get(urgency, 1)


def priority_score_to_label(score: int) -> PriorityLevel:
    """Convierte score numérico (1-9) a PriorityLevel del Reto 1."""
    if score >= 7:
        return PriorityLevel.CRITICA
    elif score >= 5:
        return PriorityLevel.ALTA
    elif score >= 3:
        return PriorityLevel.MEDIA
    else:
        return PriorityLevel.BAJA


def determine_next_status(session, fast_track: bool = False) -> IncidentStatus:
    """
    Determina el siguiente estado del incidente basándose en los campos actuales.
    
    Transiciones:
      TRIAGE / PENDING_INFO → si faltan campos → PENDING_INFO
      TRIAGE / PENDING_INFO → si todo completo → READY_TO_CREATE
      READY_TO_CREATE → (tras crear en Jira) → TICKET_CREATED
      TICKET_CREATED → CLOSED (manual o por timeout)
    
    En fast-track, solo se requieren description + category.
    """
    if session.status in (IncidentStatus.TICKET_CREATED, IncidentStatus.CLOSED):
        return session.status

    missing = get_missing_fields(session, fast_track=fast_track)

    if len(missing) == 0:
        return IncidentStatus.READY_TO_CREATE
    else:
        return IncidentStatus.PENDING_INFO


# ──────────────────────────────────────────────
#  PARSERS DE ENUMS (tolerantes a variaciones)
# ──────────────────────────────────────────────

def try_parse_category(value: str | None) -> IncidentCategory | None:
    """Intenta mapear el string extraído por GPT a un enum de categoría ITSM."""
    if not value:
        return None
    value_clean = value.strip()
    
    # Intento directo por valor
    for cat in IncidentCategory:
        if cat.value.upper() == value_clean.upper():
            return cat
    
    # Intento por nombre del enum
    for cat in IncidentCategory:
        if cat.name.upper() == value_clean.upper().replace(" ", "_").replace("/", "_"):
            return cat
    
    # Búsqueda parcial: si el valor contiene la keyword principal
    value_upper = value_clean.upper()
    keyword_map = {
        "SAP": IncidentCategory.ERP_SAP,
        "ERP": IncidentCategory.ERP_SAP,
        "ACCESO": IncidentCategory.ACCESO_IAM,
        "IAM": IncidentCategory.ACCESO_IAM,
        "VPN": IncidentCategory.INFRAESTRUCTURA,
        "RED": IncidentCategory.INFRAESTRUCTURA,
        "NETWORK": IncidentCategory.INFRAESTRUCTURA,
        "HARDWARE": IncidentCategory.INFRAESTRUCTURA,
        "SOFTWARE": IncidentCategory.CATALOGO_SW,
        "MAIL": IncidentCategory.SISTEMAS_MAIL,
        "CORREO": IncidentCategory.SISTEMAS_MAIL,
        "OUTLOOK": IncidentCategory.SISTEMAS_MAIL,
        "SEGURIDAD": IncidentCategory.SEGURIDAD,
        "SECURITY": IncidentCategory.SEGURIDAD,
        "SOPORTE": IncidentCategory.SOPORTE,
        "FACTUR": IncidentCategory.FACTURACION,
        "FINANZ": IncidentCategory.FINANZAS,
        "LOGIST": IncidentCategory.LOGISTICA,
        "INVENTAR": IncidentCategory.INVENTARIO,
        "PLATAFORMA": IncidentCategory.PLATAFORMA,
        "MOVIL": IncidentCategory.PLATAFORMA_MOVIL,
        "MOBILE": IncidentCategory.PLATAFORMA_MOVIL,
        "COMPLIANCE": IncidentCategory.COMPLIANCE,
        "WORKFLOW": IncidentCategory.WORKFLOW,
        "HR": IncidentCategory.WORKFLOW_HR,
        "BACKEND": IncidentCategory.IT_BACKEND,
        "INFRA": IncidentCategory.INFRAESTRUCTURA,
        "DATOS MAESTROS": IncidentCategory.DATOS_MAESTROS,
        "PROCUREMENT": IncidentCategory.PROCUREMENT,
        "CALIDAD": IncidentCategory.CALIDAD,
        "QUALITY": IncidentCategory.CALIDAD,
    }
    for keyword, cat in keyword_map.items():
        if keyword in value_upper:
            return cat
    
    return IncidentCategory.OTROS


def try_parse_impact(value: str | None) -> ImpactLevel | None:
    """Intenta mapear el string extraído por GPT a un enum válido."""
    if not value:
        return None
    value = value.upper().strip()
    for imp in ImpactLevel:
        if imp.value == value or imp.name == value:
            return imp
    return None


def try_parse_urgency(value: str | None) -> UrgencyLevel | None:
    """Intenta mapear el string extraído por GPT a un enum válido."""
    if not value:
        return None
    value = value.upper().strip()
    for urg in UrgencyLevel:
        if urg.value == value or urg.name == value:
            return urg
    return None
