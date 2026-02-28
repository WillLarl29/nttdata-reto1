import json
import logging
from openai import OpenAI
from app.core.config import settings
from app.models.schemas import AIExtraction

logger = logging.getLogger(__name__)

# Inicializar cliente OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)

# System prompt para forzar extracción estructurada
SYSTEM_PROMPT = """Eres un asistente de clasificación de incidentes de TI para una empresa.
Tu ÚNICO trabajo es:
1. Entender el problema que reporta el usuario.
2. Extraer la información relevante en formato JSON estructurado.
3. Generar una respuesta amigable y profesional para el usuario.

REGLAS ESTRICTAS:
- Si el usuario reporta un problema, clasifícalo con intent_type = "REPORT_INCIDENT".
- Si pregunta por el estado de un ticket, usa intent_type = "ASK_STATUS".
- Para cualquier otra cosa, usa intent_type = "GENERAL_CHAT".
- Solo extrae campos que el usuario haya mencionado EXPLÍCITAMENTE. No inventes datos.
- Si falta información (categoría, impacto, urgencia), agrégala en missing_fields.
- Las categorías posibles son: HARDWARE, SOFTWARE, RED, ACCESOS, OTROS.
- Los niveles de impacto: INDIVIDUAL (solo me afecta a mí), EQUIPO (afecta a mi equipo), ORGANIZACION (toda la empresa parada).
- Los niveles de urgencia: BAJA (puede esperar), MEDIA (necesito solución hoy), ALTA (estoy bloqueado ahora mismo).
- Tu respuesta en agent_reply debe ser en ESPAÑOL, profesional y empática.
- Si faltan datos, pide UNO SOLO a la vez en agent_reply (no bombardees con preguntas).

Responde SIEMPRE en el formato JSON especificado. Sin texto adicional fuera del JSON."""


async def extract_from_message(
    user_message: str,
    conversation_history: list[dict],
    current_draft: dict | None = None
) -> AIExtraction:
    """
    Envía el mensaje del usuario + historial a OpenAI y recibe
    la extracción estructurada del incidente.
    """
    # Construir mensajes para la API
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # Agregar contexto del borrador actual si existe
    if current_draft:
        draft_context = f"""CONTEXTO ACTUAL DEL INCIDENTE (datos ya recolectados):
- Descripción: {current_draft.get('description', 'No definida')}
- Categoría: {current_draft.get('category', 'No definida')}
- Impacto: {current_draft.get('impact', 'No definido')}
- Urgencia: {current_draft.get('urgency', 'No definida')}

Usa esta información para NO volver a preguntar lo que ya se sabe."""
        messages.append({"role": "system", "content": draft_context})

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
            max_tokens=800
        )

        raw_content = response.choices[0].message.content
        logger.info(f"OpenAI raw response: {raw_content}")

        # Parsear con Pydantic para validar la estructura
        parsed = json.loads(raw_content)
        extraction = AIExtraction(**parsed)
        return extraction

    except json.JSONDecodeError as e:
        logger.error(f"OpenAI devolvió JSON inválido: {e}")
        return AIExtraction(
            intent_type="GENERAL_CHAT",
            missing_fields=[],
            agent_reply="Disculpa, tuve un problema procesando tu mensaje. ¿Podrías reformularlo?"
        )
    except Exception as e:
        logger.error(f"Error llamando a OpenAI: {e}")
        return AIExtraction(
            intent_type="GENERAL_CHAT",
            missing_fields=[],
            agent_reply="Estoy teniendo problemas técnicos momentáneos. Por favor intenta de nuevo en unos segundos."
        )
