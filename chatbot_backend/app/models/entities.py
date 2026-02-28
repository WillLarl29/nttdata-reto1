import enum
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum, ForeignKey, Integer
from sqlalchemy.orm import relationship
from app.models.database import Base


# ──────────────────────────────────────────────
#  ENUMS DE NEGOCIO
# ──────────────────────────────────────────────

class IncidentStatus(str, enum.Enum):
    """Máquina de estados del incidente."""
    TRIAGE = "TRIAGE"
    PENDING_INFO = "PENDING_INFO"
    READY_TO_CREATE = "READY_TO_CREATE"
    TICKET_CREATED = "TICKET_CREATED"
    CLOSED = "CLOSED"


class IncidentCategory(str, enum.Enum):
    """Categorías que GPT puede extraer del mensaje del usuario."""
    HARDWARE = "HARDWARE"
    SOFTWARE = "SOFTWARE"
    NETWORK = "RED"
    ACCESS = "ACCESOS"
    OTHER = "OTROS"


class ImpactLevel(str, enum.Enum):
    """Nivel de impacto del incidente."""
    INDIVIDUAL = "INDIVIDUAL"       # Valor numérico: 1
    TEAM = "EQUIPO"                 # Valor numérico: 2
    ORGANIZATION = "ORGANIZACION"   # Valor numérico: 3


class UrgencyLevel(str, enum.Enum):
    """Nivel de urgencia del incidente."""
    LOW = "BAJA"       # Valor numérico: 1
    MEDIUM = "MEDIA"   # Valor numérico: 2
    HIGH = "ALTA"      # Valor numérico: 3


# ──────────────────────────────────────────────
#  MODELOS ORM
# ──────────────────────────────────────────────

class IncidentSession(Base):
    """
    Representa una sesión de conversación con un usuario.
    Contiene el estado actual del borrador del incidente 
    que se va llenando progresivamente con cada mensaje.
    """
    __tablename__ = "incident_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    user_email = Column(String(255), nullable=False)
    status = Column(SAEnum(IncidentStatus), default=IncidentStatus.TRIAGE, nullable=False)

    # Campos que se van llenando progresivamente (el "borrador" del ticket)
    description = Column(Text, nullable=True)
    category = Column(SAEnum(IncidentCategory), nullable=True)
    impact = Column(SAEnum(ImpactLevel), nullable=True)
    urgency = Column(SAEnum(UrgencyLevel), nullable=True)
    calculated_priority = Column(Integer, nullable=True)  # Impacto × Urgencia

    # Datos de Jira (se llenan al crear el ticket)
    jira_issue_key = Column(String(32), nullable=True)   # Ej: "IT-402"
    jira_issue_url = Column(String(512), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relación con mensajes
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<IncidentSession(session_id='{self.session_id}', status='{self.status}')>"


class ChatMessage(Base):
    """
    Almacena cada mensaje individual de la conversación.
    Sirve para construir el historial que se envía a OpenAI como contexto
    y para auditoría.
    """
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("incident_sessions.session_id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # "user" o "assistant"
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relación inversa
    session = relationship("IncidentSession", back_populates="messages")

    def __repr__(self):
        return f"<ChatMessage(role='{self.role}', session_id='{self.session_id}')>"
