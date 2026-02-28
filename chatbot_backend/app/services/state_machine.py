"""
Máquina de estados del incidente.
Decide transiciones y calcula prioridad basándose en los campos
recolectados progresivamente.
"""
from app.models.entities import IncidentStatus, IncidentCategory, ImpactLevel, UrgencyLevel


# Campos obligatorios para poder crear un ticket en Jira
REQUIRED_FIELDS = ["description", "category", "impact", "urgency"]

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


def get_missing_fields(session) -> list[str]:
    """
    Revisa qué campos obligatorios del borrador aún están vacíos.
    Retorna lista de nombres de campos faltantes.
    """
    missing = []
    if not session.description:
        missing.append("description")
    if not session.category:
        missing.append("category")
    if not session.impact:
        missing.append("impact")
    if not session.urgency:
        missing.append("urgency")
    return missing


def calculate_priority(impact: ImpactLevel, urgency: UrgencyLevel) -> int:
    """
    Calcula prioridad como Impacto × Urgencia.
    Resultado: 1 (mínima) a 9 (máxima/crítica).
    """
    return IMPACT_VALUES[impact] * URGENCY_VALUES[urgency]


def determine_next_status(session) -> IncidentStatus:
    """
    Determina el siguiente estado del incidente basándose en los campos actuales.
    
    Transiciones:
      TRIAGE / PENDING_INFO → si faltan campos → PENDING_INFO
      TRIAGE / PENDING_INFO → si todo completo → READY_TO_CREATE
      READY_TO_CREATE → (tras crear en Jira) → TICKET_CREATED
      TICKET_CREATED → CLOSED (manual o por timeout)
    """
    # Si ya tiene ticket, no cambiar
    if session.status in (IncidentStatus.TICKET_CREATED, IncidentStatus.CLOSED):
        return session.status

    missing = get_missing_fields(session)

    if len(missing) == 0:
        return IncidentStatus.READY_TO_CREATE
    else:
        return IncidentStatus.PENDING_INFO


def try_parse_category(value: str | None) -> IncidentCategory | None:
    """Intenta mapear el string extraído por GPT a un enum válido."""
    if not value:
        return None
    value = value.upper().strip()
    for cat in IncidentCategory:
        if cat.value == value or cat.name == value:
            return cat
    return None


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
