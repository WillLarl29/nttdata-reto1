import json
import logging
from openai import OpenAI
from app.core.config import settings
from app.models.schemas import AIExtraction
from app.models.entities import IncidentCategory

logger = logging.getLogger(__name__)

# Inicializar cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# Generar catálogo de categorías dinámicamente desde el enum
_CATEGORY_LIST = "\n".join([f"  - {cat.value}" for cat in IncidentCategory])

# System prompt actualizado para Reto 1: ITSM enterprise
SYSTEM_PROMPT = (
    "Eres un asistente de clasificación de incidentes de TI para una empresa grande (enterprise ITSM).\n"
    "Tu ÚNICO trabajo es:\n"
    "1. Entender el problema que reporta el usuario.\n"
    "2. Extraer la información relevante en formato JSON estructurado.\n"
    "3. Generar una respuesta amigable y profesional para el usuario.\n"
    "\n"
    "REGLAS ESTRICTAS:\n"
    "\n"
    "INTENCIONES (MUY IMPORTANTE):\n"
    "- Si el usuario describe CUALQUIER problema técnico, equipo dañado, software que falla, servicio que no funciona, o pide ayuda con algo de TI, SIEMPRE clasifícalo como intent_type = \"REPORT_INCIDENT\".\n"
    "- Ejemplos de REPORT_INCIDENT: \"mi laptop se malogró\", \"no prende mi PC\", \"no puedo acceder\", \"se me colgó el sistema\", \"no me funciona el correo\", \"mi equipo está lento\".\n"
    '- Si pregunta por el estado de un ticket, usa intent_type = "ASK_STATUS".\n'
    '- Solo usa "GENERAL_CHAT" si el usuario hace una pregunta NO relacionada con TI (ej: "hola", "gracias", "cómo estás").\n'
    '- EN CASO DE DUDA, usa "REPORT_INCIDENT". Es mejor registrar un incidente de más que perder uno.\n'
    "\n"
    "CLASIFICACIÓN – CATEGORÍAS ITSM:\n"
    "Las categorías posibles son:\n"
    + _CATEGORY_LIST + "\n"
    "\n"
    "Usa la categoría que mejor describa el problema. Si ninguna aplica, usa \"Otros\".\n"
    "\n"
    "EXTRACCIÓN DE CAMPOS:\n"
    "- Solo extrae campos que el usuario haya mencionado EXPLÍCITAMENTE. No inventes datos.\n"
    "- extracted_description: resumen breve del problema.\n"
    "- extracted_category: una de las categorías listadas arriba (valor exacto).\n"
    "- extracted_sub_category: subcategoría más específica (texto libre, ej: \"Autenticación/Permisos\").\n"
    "- extracted_impact: INDIVIDUAL (solo me afecta a mí), EQUIPO (afecta a mi equipo), ORGANIZACION (toda la empresa).\n"
    "- extracted_urgency: BAJA (puede esperar), MEDIA (necesito solución hoy), ALTA (estoy bloqueado ahora mismo).\n"
    "- extracted_service: sistema o servicio afectado (ej: \"SAP\", \"VPN\", \"Outlook\").\n"
    "- extracted_environment: ambiente (PROD, QA, DEV). Si no lo menciona, asume PROD.\n"
    "- extracted_assignment_group: grupo de soporte sugerido basado en la categoría.\n"
    "\n"
    "EXPLICABILIDAD (MUY IMPORTANTE):\n"
    "- confidence: tu nivel de confianza en la clasificación (0.0 a 1.0).\n"
    "- evidence_snippets: fragmentos EXACTOS del texto del usuario que justifican tu clasificación.\n"
    "- assumptions: supuestos que hiciste (ej: \"Asumí que es urgente porque mencionó facturación\").\n"
    "- rules_used: reglas o patrones que aplicaste (ej: \"Error 403 + servicio crítico => Alta urgencia\").\n"
    "\n"
    "FAST-TRACK (incidentes críticos):\n"
    "- is_critical: true si detectas un incidente que afecta a toda la organización o un servicio crítico caído.\n"
    '  Ejemplos: "servidor caído", "SAP no funciona para nadie", "email corporativo no funciona".\n'
    "  Si es critical, puedes omitir preguntar impacto/urgencia (se asumen máximos).\n"
    "\n"
    "CAMPOS FALTANTES:\n"
    "- Si falta información (categoría, impacto, urgencia), agrégala en missing_fields.\n"
    "- En agent_reply, pide UN SOLO campo a la vez (no bombardees con preguntas).\n"
    "\n"
    "RESPUESTA:\n"
    "- agent_reply debe ser en ESPAÑOL, profesional y empática.\n"
    "- Si es un incidente crítico, prioriza rapidez sobre completitud.\n"
    "\n"
    "Responde SIEMPRE en formato JSON válido. Sin texto adicional fuera del JSON."
)


async def extract_from_message(
    user_message: str,
    conversation_history: list[dict],
    current_draft: dict | None = None
) -> AIExtraction:
    """
    Envía el mensaje del usuario + historial a OpenAI y recibe
    la extracción estructurada y enriquecida del incidente.
    """
    # Construir mensajes para la API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Agregar contexto del borrador actual si existe
    if current_draft:
        draft_parts = [
            "CONTEXTO ACTUAL DEL INCIDENTE (datos ya recolectados):",
            f"- Descripción: {current_draft.get('description', 'No definida')}",
            f"- Categoría: {current_draft.get('category', 'No definida')}",
            f"- Subcategoría: {current_draft.get('sub_category', 'No definida')}",
            f"- Impacto: {current_draft.get('impact', 'No definido')}",
            f"- Urgencia: {current_draft.get('urgency', 'No definida')}",
            f"- Servicio: {current_draft.get('service', 'No definido')}",
            f"- Ambiente: {current_draft.get('environment', 'No definido')}",
            "",
            "Usa esta información para NO volver a preguntar lo que ya se sabe.",
        ]
        messages.append({"role": "system", "content": "\n".join(draft_parts)})

    # Agregar historial de conversación (últimos 10 mensajes para no exceder tokens)
    for msg in conversation_history[-10:]:
        messages.append({"role": msg["role"], "content": msg["content"]})

    # Agregar mensaje actual del usuario
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,  # Bajo para reducir creatividad / alucinaciones
            max_tokens=1200   # Aumentado para soportar campos de explicabilidad
        )

        raw_content = response.choices[0].message.content
        logger.info(f"OpenAI raw response: {raw_content}")

        # Parsear con Pydantic para validar la estructura
        parsed = json.loads(raw_content)
        extraction = AIExtraction(**parsed)
        return extraction

    except json.JSONDecodeError as e:
        logger.warning(f"OpenAI devolvió JSON inválido, usando clasificador local: {e}")
        from app.services.fallback_classifier import classify_locally
        return classify_locally(user_message, conversation_history, current_draft)
    except Exception as e:
        logger.warning(f"OpenAI no disponible, usando clasificador local: {e}")
        from app.services.fallback_classifier import classify_locally
        return classify_locally(user_message, conversation_history, current_draft)
