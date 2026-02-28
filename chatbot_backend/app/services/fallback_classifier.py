"""
Clasificador local basado en reglas (fallback).
Se usa cuando OpenAI no está disponible para que el chatbot
siga funcionando con clasificación básica por keywords.
"""
import re
from app.models.schemas import AIExtraction


# ──────────────────────────────────────────────
#  REGLAS DE CLASIFICACIÓN POR KEYWORDS
# ──────────────────────────────────────────────

CATEGORY_RULES = [
    # (keywords, category, sub_category, assignment_group)
    (["sap", "erp", "transacción", "transaccion"], "ERP / SAP", "Acceso/Funcionalidad SAP", "Soporte SAP"),
    (["factura", "facturación", "facturacion", "cobro", "pago"], "Facturación", "Proceso de facturación", "Finanzas"),
    (["acceso", "login", "contraseña", "password", "403", "401", "permiso", "autenticación", "autenticacion"], "Acceso / IAM", "Autenticación/Permisos", "Soporte IAM"),
    (["vpn", "red", "internet", "wifi", "conexión", "conexion", "proxy", "firewall"], "Infraestructura", "Conectividad/Red", "Infraestructura"),
    (["correo", "email", "outlook", "mail", "exchange"], "Sistemas / Mail", "Correo corporativo", "Soporte Mail"),
    (["servidor", "server", "caído", "caido", "down", "outage"], "Infraestructura", "Servidor/Disponibilidad", "Infraestructura"),
    (["impresora", "printer", "escáner", "escaner", "hardware", "monitor", "teclado", "mouse", "laptop", "computadora", "pc", "notebook", "pantalla", "disco duro", "batería", "bateria", "cargador", "no prende", "no enciende", "malogro", "malogró", "dañó", "roto"], "Infraestructura", "Hardware/Periféricos", "Soporte Hardware"),
    (["software", "instalar", "instalación", "instalacion", "actualizar", "licencia", "programa"], "Catálogo / SW", "Software/Licencias", "Soporte SW"),
    (["seguridad", "virus", "malware", "phishing", "ransomware", "hackeo"], "Seguridad", "Incidente de seguridad", "Seguridad IT"),
    (["teléfono", "telefono", "movil", "celular", "app", "aplicación", "aplicacion"], "Plataforma / Movil", "App móvil", "Soporte Apps"),
    (["workflow", "aprobación", "aprobacion", "flujo", "proceso"], "Workflow", "Flujo de trabajo", "Soporte Procesos"),
    (["inventario", "stock", "almacén", "almacen"], "Inventario", "Gestión de inventario", "Logística"),
    (["logística", "logistica", "envío", "envio", "despacho"], "Logística", "Proceso logístico", "Logística"),
    (["rrhh", "nómina", "nomina", "vacaciones", "personal"], "Workflow / HR", "RRHH/Nómina", "Soporte RRHH"),
]

URGENCY_KEYWORDS = {
    "ALTA": ["urgente", "bloqueado", "caído", "caido", "no funciona", "paralizado", "crítico", "critico", "ahora mismo", "inmediato", "no prende", "no enciende", "malogro", "malogró", "dejó de funcionar", "dejo de funcionar"],
    "MEDIA": ["hoy", "pronto", "necesito", "importante", "lento", "se traba", "falla"],
    "BAJA": ["cuando pueda", "no urgente", "consulta", "duda"],
}

IMPACT_KEYWORDS = {
    "ORGANIZACION": ["toda la empresa", "todos", "nadie puede", "completo", "general", "masivo"],
    "EQUIPO": ["equipo", "departamento", "área", "area", "grupo", "varios", "compañeros"],
    "INDIVIDUAL": ["yo", "mi", "solo a mí", "solo a mi", "solamente"],
}

CRITICAL_KEYWORDS = ["servidor caído", "servidor caido", "caída total", "caida total", "no funciona para nadie", "toda la empresa", "servicio caído", "servicio caido", "outage", "sistema completo"]

# Mensajes de repregunta por campo
FIELD_QUESTIONS = {
    "category": "¿Podrías indicarme qué tipo de sistema o servicio está afectado? Por ejemplo: SAP, correo, red/VPN, software, accesos, etc.",
    "impact": "¿A cuántas personas afecta este problema? ¿Solo a ti, a tu equipo, o a toda la organización?",
    "urgency": "¿Qué tan urgente es? ¿Puedes esperar, lo necesitas hoy, o estás completamente bloqueado ahora mismo?",
}


def _detect_keywords(text: str, keyword_list: list[str]) -> bool:
    """Verifica si alguna keyword está en el texto."""
    text_lower = text.lower()
    return any(kw in text_lower for kw in keyword_list)


def _detect_category(text: str) -> tuple[str | None, str | None, str | None]:
    """Detecta categoría, subcategoría y grupo de soporte por keywords."""
    text_lower = text.lower()
    for keywords, category, sub_cat, group in CATEGORY_RULES:
        if any(kw in text_lower for kw in keywords):
            return category, sub_cat, group
    return None, None, None


def _detect_urgency(text: str) -> str | None:
    text_lower = text.lower()
    for level, keywords in URGENCY_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return level
    return None


def _detect_impact(text: str) -> str | None:
    text_lower = text.lower()
    for level, keywords in IMPACT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return level
    return None


def _detect_critical(text: str) -> bool:
    text_lower = text.lower()
    return any(kw in text_lower for kw in CRITICAL_KEYWORDS)


def _extract_service(text: str) -> str | None:
    """Intenta extraer el nombre del servicio del texto."""
    services = ["SAP", "VPN", "Outlook", "Exchange", "Teams", "Windows", "Office", "Oracle", "Jira", "Salesforce", "SharePoint"]
    for svc in services:
        if svc.lower() in text.lower():
            return svc
    return None


def classify_locally(
    user_message: str,
    conversation_history: list[dict],
    current_draft: dict | None = None
) -> AIExtraction:
    """
    Clasificador local basado en reglas.
    Analiza el mensaje del usuario con keywords y genera una extracción
    que sigue el mismo esquema que OpenAI.
    """
    full_text = user_message
    # Incluir historial completo para mejor detección
    for msg in (conversation_history or []):
        if msg["role"] == "user":
            full_text += " " + msg["content"]

    # Detectar si es un reporte de incidente (amplio para español coloquial)
    incident_keywords = [
        "error", "no funciona", "problema", "falla", "caído", "caido",
        "no puedo", "bloqueado", "ayuda", "urgente", "acceso", "permiso",
        "malogro", "malogró", "no prende", "no enciende", "se colgó",
        "se colgo", "se trabó", "se trabo", "lento", "dejó de",
        "dejo de", "no funciona", "no sirve", "dañó", "roto",
        "pantalla azul", "reinicia solo", "no carga", "no abre",
        "laptop", "computadora", "pc", "equipo", "impresora",
    ]
    is_incident = _detect_keywords(user_message, incident_keywords) or (current_draft and current_draft.get("description"))
    
    if not is_incident:
        # Chat general
        return AIExtraction(
            intent_type="GENERAL_CHAT",
            missing_fields=[],
            confidence=0.5,
            evidence_snippets=[],
            assumptions=["No se detectaron keywords de incidente en el mensaje"],
            rules_used=["Clasificación por keywords locales (fallback)"],
            agent_reply="¡Hola! Soy GenIA, tu asistente de soporte TI. ¿En qué puedo ayudarte? Si tienes un incidente, descríbeme el problema y te ayudaré a registrarlo."
        )

    # Es un incidente - extraer campos
    category, sub_cat, group = _detect_category(full_text)
    urgency = _detect_urgency(full_text)
    impact = _detect_impact(full_text)
    service = _extract_service(full_text)
    is_critical = _detect_critical(full_text)

    # Verificar qué ya tenemos del draft
    has_description = bool(current_draft and current_draft.get("description"))
    has_category = bool(current_draft and current_draft.get("category")) or bool(category)
    has_impact = bool(current_draft and current_draft.get("impact")) or bool(impact)
    has_urgency = bool(current_draft and current_draft.get("urgency")) or bool(urgency)

    # Determinar campos faltantes
    missing = []
    if not has_category:
        missing.append("category")
    if not has_impact and not is_critical:
        missing.append("impact")
    if not has_urgency and not is_critical:
        missing.append("urgency")

    # Construir respuesta amigable
    if is_critical:
        reply = (
            "🚨 Entiendo que es un incidente crítico. Estoy registrando tu reporte de manera prioritaria. "
            "Se asignará con la máxima prioridad al equipo correspondiente."
        )
    elif missing:
        # Preguntar por el primer campo faltante
        first_missing = missing[0]
        reply = f"Entendido, estoy registrando tu incidente. {FIELD_QUESTIONS.get(first_missing, '¿Podrías darme más detalles?')}"
    else:
        reply = (
            "Perfecto, tengo toda la información necesaria. "
            "Voy a crear el ticket en Jira con los datos proporcionados."
        )

    # Evidencias
    evidence = []
    if category:
        evidence.append(f"Categoría detectada: {category}")
    if urgency:
        evidence.append(f"Urgencia detectada: {urgency}")
    if impact:
        evidence.append(f"Impacto detectado: {impact}")
    if service:
        evidence.append(f"Servicio: {service}")

    return AIExtraction(
        intent_type="REPORT_INCIDENT",
        extracted_description=user_message[:200] if not has_description else None,
        extracted_category=category,
        extracted_sub_category=sub_cat,
        extracted_impact=impact if not is_critical else "ORGANIZACION",
        extracted_urgency=urgency if not is_critical else "ALTA",
        extracted_service=service,
        extracted_environment="PROD",
        extracted_assignment_group=group,
        confidence=0.7 if category else 0.4,
        evidence_snippets=evidence,
        assumptions=["Clasificación basada en reglas locales (modo fallback)"],
        rules_used=["Keyword matching para categoría/urgencia/impacto"],
        is_critical=is_critical,
        missing_fields=missing,
        agent_reply=reply,
    )
