"""
Plantilla de Incidente Enriquecido por GenIA (Reto 1).
Genera el texto de 7 secciones para publicar como comentario en Jira.
Incluye conversión a ADF (Atlassian Document Format).
"""
from datetime import datetime
from typing import Any, Dict, List


# ──────────────────────────────────────────────
#  PLANTILLA MARKDOWN (7 secciones)
# ──────────────────────────────────────────────

INCIDENT_TEMPLATE_PRO = """\
# 🧠 GenIA – Incidente Enriquecido (ITSM)

## 1) Contexto del Ticket (Entrada)
**Ticket:** {issue_key}
**Creado:** {created_at}
**Reportado por:** {reporter_email}
**Canal:** {channel}
**Resumen:** {summary}

**Descripción original (usuario):**
{original_description}

---

## 2) Clasificación Automática (Agente Clasificador)
- **Tipo ITSM:** {ticket_type}
- **Categoría:** {category}
- **Subcategoría:** {sub_category}
- **Servicio/Sistema:** {service}
- **Ambiente:** {environment}
- **Grupo sugerido:** {assignment_group}
- **Confianza del modelo:** {confidence_pct}

**Campos faltantes detectados:**
{missing_fields}

---

## 3) Priorización (Agente de Priorización)
- **Impacto:** {impact}
- **Urgencia:** {urgency}
- **Prioridad:** {priority}

**Justificación (explicable):**
- **Evidencias del texto:** {evidence_snippets}
- **Supuestos:** {assumptions}
- **Reglas aplicadas:** {rules_used}

---

## 4) Respuesta sugerida al usuario (Agente de Soporte)
**Mensaje listo para enviar:**
{user_reply_draft}

---

## 5) Acciones recomendadas (Orquestador)
**Próximos pasos internos:**
{next_steps}

**Etiquetas sugeridas:**
{suggested_labels}

---

## 6) Auditoría / Trazabilidad
- **Procesado por:** {assistant_version}
- **Fecha de procesamiento:** {processed_at}
"""


def _bullet_list(items: List[str], empty_text: str = "-") -> str:
    if not items:
        return empty_text
    return "\n".join([f"- {x}" for x in items])


def _inline_list(items: List[str], empty_text: str = "-") -> str:
    if not items:
        return empty_text
    return ", ".join(items)


def render_incident_template_pro(
    issue: Dict[str, Any],
    enrichment: Dict[str, Any],
    assistant_version: str = "GenIA-ITSM v1"
) -> str:
    """
    Renderiza la plantilla profesional con datos del issue y enriquecimiento de la IA.
    
    Args:
        issue: Datos del ticket (issue_key, reporter_email, description, etc.)
        enrichment: Datos de enriquecimiento (classification, prioritization, explainability, etc.)
        assistant_version: Versión del asistente para trazabilidad.
    
    Returns:
        Texto Markdown renderizado con las 7 secciones.
    """
    now = datetime.now().isoformat(timespec="seconds")

    # Inputs
    issue_key = issue.get("issue_key", "-")
    created_at = issue.get("created_at", "-")
    reporter_email = issue.get("reporter_email", "-")
    channel = issue.get("channel", "chat")
    summary = issue.get("summary", "-")
    original_description = issue.get("description", "-")

    # Enrichment
    cls = enrichment.get("classification", {})
    prio = enrichment.get("prioritization", {})
    exp = enrichment.get("explainability", {})

    confidence = cls.get("confidence", None)
    confidence_pct = f"{confidence * 100:.0f}%" if isinstance(confidence, (float, int)) else "-"

    # Labels sugeridos
    labels = ["genai_processed"]
    cat_label = cls.get("category", "")
    if cat_label:
        labels.append(cat_label.lower().replace(" / ", "_").replace(" ", "_"))
    prio_label = prio.get("priority", "")
    if prio_label:
        labels.append(f"p_{prio_label.lower()}")

    filled = INCIDENT_TEMPLATE_PRO.format(
        issue_key=issue_key,
        created_at=created_at,
        reporter_email=reporter_email,
        channel=channel,
        summary=summary,
        original_description=original_description,

        ticket_type=cls.get("ticket_type", "INCIDENT"),
        category=cls.get("category", "-"),
        sub_category=cls.get("sub_category", "-"),
        service=cls.get("service", issue.get("service", "-")),
        environment=cls.get("environment", issue.get("environment", "-")),
        assignment_group=cls.get("assignment_group", "-"),
        confidence_pct=confidence_pct,
        missing_fields=_bullet_list(cls.get("missing_fields", [])),

        impact=prio.get("impact", "-"),
        urgency=prio.get("urgency", "-"),
        priority=prio.get("priority", "-"),

        evidence_snippets=_inline_list(exp.get("evidence_snippets", [])),
        assumptions=_inline_list(exp.get("assumptions", [])),
        rules_used=_inline_list(exp.get("rules_used", [])),

        user_reply_draft=enrichment.get("user_reply_draft", "-"),
        next_steps=_bullet_list(enrichment.get("next_steps", [])),
        suggested_labels=_inline_list(labels),

        assistant_version=assistant_version,
        processed_at=now,
    )
    return filled


# ──────────────────────────────────────────────
#  CONVERSIÓN A ADF (Atlassian Document Format)
# ──────────────────────────────────────────────

def adf_from_plain_text(text: str) -> dict:
    """
    Convierte texto con saltos de línea a ADF (paragraphs).
    Se usa para publicar comentarios en Jira Cloud API v3.
    """
    paragraphs = []
    for line in text.splitlines():
        paragraphs.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line if line else " "}]
        })
    return {"type": "doc", "version": 1, "content": paragraphs}


def build_enrichment_from_session(session, extraction) -> Dict[str, Any]:
    """
    Construye el dict 'enrichment' a partir de la sesión y la extracción,
    listo para pasar a render_incident_template_pro.
    """
    return {
        "classification": {
            "ticket_type": "INCIDENT",
            "category": session.category.value if session.category else "-",
            "sub_category": session.sub_category or "-",
            "service": session.service or "-",
            "environment": session.environment or "-",
            "assignment_group": session.assignment_group or "-",
            "confidence": session.ai_confidence,
            "missing_fields": [],
        },
        "prioritization": {
            "impact": session.impact.value if session.impact else "-",
            "urgency": session.urgency.value if session.urgency else "-",
            "priority": session.priority_label.value if session.priority_label else "-",
        },
        "explainability": {
            "evidence_snippets": extraction.evidence_snippets if extraction else [],
            "assumptions": extraction.assumptions if extraction else [],
            "rules_used": extraction.rules_used if extraction else [],
        },
        "user_reply_draft": extraction.agent_reply if extraction else "-",
        "next_steps": [
            f"Asignar a {session.assignment_group or 'equipo correspondiente'}",
            "Validar datos reportados",
            "Contactar usuario si se requiere más info",
        ],
    }
