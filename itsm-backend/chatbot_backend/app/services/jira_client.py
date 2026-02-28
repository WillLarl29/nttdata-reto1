import logging
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

# Base URL para la API REST de Jira Cloud v2
JIRA_API_BASE = f"{settings.JIRA_DOMAIN}/rest/api/2"


def _get_auth() -> tuple[str, str]:
    """Retorna la tupla (email, token) para Basic Auth de Jira Cloud."""
    return (settings.JIRA_USER_EMAIL, settings.JIRA_API_TOKEN)


def _get_headers() -> dict:
    """Headers estándar para Jira REST API."""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }


# Mapeo de prioridad numérica interna → nombre de prioridad en Jira
PRIORITY_MAP = {
    1: "Lowest",
    2: "Low",
    3: "Medium",
    4: "Medium",
    5: "High",
    6: "High",
    7: "Highest",
    8: "Highest",
    9: "Highest",
}


async def create_jira_issue(
    summary: str,
    description: str,
    category: str,
    priority_score: int,
    reporter_email: str
) -> dict:
    """
    Crea un Issue en Jira Cloud usando la REST API v2.
    
    Retorna dict con:
      - key: "IT-402"
      - url: "https://dominio.atlassian.net/browse/IT-402"
    O lanza excepción si falla.
    """
    jira_priority = PRIORITY_MAP.get(priority_score, "Medium")

    payload = {
        "fields": {
            "project": {
                "key": settings.JIRA_PROJECT_KEY
            },
            "summary": summary,
            "description": description,
            "issuetype": {
                "name": "Task"  # Usar "Bug" o "Incident" si el proyecto lo soporta
            },
            "priority": {
                "name": jira_priority
            },
            "labels": [
                "chatbot-incidentes",
                category.lower()
            ]
        }
    }

    logger.info(f"Creando issue en Jira: {summary} | prioridad={jira_priority}")

    # Intentar hasta 3 veces con backoff simple
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{JIRA_API_BASE}/issue",
                    json=payload,
                    auth=_get_auth(),
                    headers=_get_headers()
                )

            if response.status_code == 201:
                data = response.json()
                issue_key = data["key"]
                issue_url = f"{settings.JIRA_DOMAIN}/browse/{issue_key}"
                logger.info(f"✅ Issue creado exitosamente: {issue_key}")
                return {"key": issue_key, "url": issue_url}
            else:
                logger.error(
                    f"Jira respondió {response.status_code} (intento {attempt}/{max_retries}): "
                    f"{response.text}"
                )
                if attempt == max_retries:
                    raise Exception(
                        f"Jira API error {response.status_code}: {response.text}"
                    )

        except httpx.TimeoutException:
            logger.warning(f"Timeout en Jira (intento {attempt}/{max_retries})")
            if attempt == max_retries:
                raise Exception("Jira API timeout después de 3 intentos")
        except httpx.ConnectError as e:
            logger.error(f"No se pudo conectar a Jira: {e}")
            raise Exception(f"No se pudo conectar a Jira: {e}")

    raise Exception("Error inesperado creando issue en Jira")
