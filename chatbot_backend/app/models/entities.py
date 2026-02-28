import enum
import json
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Enum as SAEnum, ForeignKey, Integer, Float
from sqlalchemy.orm import relationship
from app.models.database import Base


# ──────────────────────────────────────────────
#  ENUMS DE NEGOCIO (Reto 1 – ITSM Enterprise)
# ──────────────────────────────────────────────

class IncidentStatus(str, enum.Enum):
    """Máquina de estados del incidente."""
    TRIAGE = "TRIAGE"
    PENDING_INFO = "PENDING_INFO"
    READY_TO_CREATE = "READY_TO_CREATE"
    TICKET_CREATED = "TICKET_CREATED"
    CLOSED = "CLOSED"


class IncidentCategory(str, enum.Enum):
    """Categorías ITSM alineadas al Reto 1 (~25 consolidadas)."""
    ACCESO_IAM = "Acceso / IAM"
    ACCESO_ROLES = "Acceso / Roles"
    ERP_SAP = "ERP / SAP"
    ERP_FINANZAS = "ERP / Finanzas"
    WORKFLOW_HR = "Workflow / HR"
    WORKFLOW = "Workflow"
    LOGISTICA_IT = "Logística / IT"
    LOGISTICA = "Logística"
    PLATAFORMA = "Plataforma"
    PLATAFORMA_MOVIL = "Plataforma / Movil"
    ASSET_MGMT = "Asset Mgmt"
    ASSET_QUALITY = "Asset Quality"
    FINANZAS = "Finanzas"
    FACTURACION = "Facturación"
    SISTEMAS_MAIL = "Sistemas / Mail"
    CATALOGO_SW = "Catálogo / SW"
    CATALOGO = "Catálogo"
    IT_BACKEND = "IT / Backend"
    INFRAESTRUCTURA = "Infraestructura"
    DATOS_MAESTROS = "Datos Maestros"
    SOPORTE = "Soporte"
    SOPORTE_VIP = "Soporte / VIP"
    SOPORTE_GESTION = "Soporte / Gestión"
    SOPORTE_ASSET = "Soporte / Asset"
    SOPORTE_IA = "Soporte / IA"
    IAM_SEGURIDAD = "IAM / Seguridad"
    SECURITY_ENDPOINT = "Security / Endpoint"
    SEGURIDAD = "Seguridad"
    COMPLIANCE = "Compliance"
    PROCUREMENT = "Procurement"
    INVENTARIO = "Inventario"
    ADMINISTRACION = "Administración"
    COMUNICACION = "Comunicación"
    CALIDAD = "Calidad"
    SISTEMA = "Sistema"
    OTROS = "Otros"


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


class PriorityLevel(str, enum.Enum):
    """Nivel de prioridad calculada (visible en Jira)."""
    BAJA = "Baja"
    MEDIA = "Media"
    ALTA = "Alta"
    CRITICA = "Crítica"


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

    # Campos del borrador – se llenan progresivamente
    description = Column(Text, nullable=True)
    category = Column(SAEnum(IncidentCategory), nullable=True)
    sub_category = Column(String(128), nullable=True)
    impact = Column(SAEnum(ImpactLevel), nullable=True)
    urgency = Column(SAEnum(UrgencyLevel), nullable=True)
    calculated_priority = Column(Integer, nullable=True)  # Impacto × Urgencia (1-9)
    priority_label = Column(SAEnum(PriorityLevel), nullable=True)

    # Campos enriquecidos – Reto 1
    service = Column(String(128), nullable=True)         # Sistema/servicio afectado (SAP, VPN, etc.)
    environment = Column(String(32), nullable=True)      # PROD, QA, DEV
    assignment_group = Column(String(128), nullable=True) # Grupo de soporte sugerido
    channel = Column(String(32), default="chat")          # Canal de origen

    # IA – Trazabilidad
    ai_confidence = Column(Float, nullable=True)         # Confianza del modelo (0-1)
    ai_reasoning = Column(Text, nullable=True)           # JSON: evidencias, supuestos, reglas

    # Datos de Jira (se llenan al crear el ticket)
    jira_issue_key = Column(String(32), nullable=True)   # Ej: "IT-402"
    jira_issue_url = Column(String(512), nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relaciones
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")
    decisions = relationship("AIDecisionLog", back_populates="session", cascade="all, delete-orphan")

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


class AIDecisionLog(Base):
    """
    Registro de auditoría para cada decisión de la IA.
    Permite trazabilidad completa de por qué se clasificó/priorizó así.
    """
    __tablename__ = "ai_decision_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("incident_sessions.session_id"), nullable=False, index=True)
    step_name = Column(String(64), nullable=False)  # "classification", "prioritization", "support"
    input_data = Column(Text, nullable=True)         # JSON del input enviado a OpenAI
    output_data = Column(Text, nullable=True)        # JSON del output recibido
    confidence = Column(Float, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relación inversa
    session = relationship("IncidentSession", back_populates="decisions")

    def __repr__(self):
        return f"<AIDecisionLog(step='{self.step_name}', session_id='{self.session_id}')>"
