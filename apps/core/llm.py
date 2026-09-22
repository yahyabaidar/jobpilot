import json
import logging
import re
import time

from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60.0

_client: OpenAI | None = None


class LLMError(Exception):
    pass


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(base_url=settings.LLM_BASE_URL, api_key=settings.LLM_API_KEY)
    return _client


def _try_parse_json(text: str) -> dict | None:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return None

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        return None


def _call(client: OpenAI, messages: list[dict], timeout: float) -> str:
    started = time.monotonic()
    try:
        response = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=messages,
            response_format={"type": "json_object"},
            timeout=timeout,
        )
    except Exception as exc:
        raise LLMError(f"Appel au modèle IA échoué : {exc}") from exc
    duration = time.monotonic() - started

    usage = response.usage
    logger.info(
        "llm call model=%s duration=%.2fs prompt_tokens=%s completion_tokens=%s",
        settings.LLM_MODEL,
        duration,
        getattr(usage, "prompt_tokens", None),
        getattr(usage, "completion_tokens", None),
    )
    return response.choices[0].message.content


def complete_json(
    prompt: str, system: str, schema_hint: str = "", *, timeout: float = DEFAULT_TIMEOUT
) -> dict:
    """Ask the LLM for a JSON response and parse it, retrying once on malformed JSON."""
    client = get_client()
    user_content = f"{prompt}\n\n{schema_hint}" if schema_hint else prompt
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user_content},
    ]

    content = _call(client, messages, timeout)
    data = _try_parse_json(content)
    if data is not None:
        return data

    logger.warning("llm response was not valid JSON, retrying once model=%s", settings.LLM_MODEL)
    retry_messages = [
        *messages,
        {"role": "assistant", "content": content},
        {
            "role": "user",
            "content": "Ta réponse précédente n'était pas un JSON valide. "
            "Renvoie uniquement le JSON demandé, sans aucun texte autour.",
        },
    ]
    retry_content = _call(client, retry_messages, timeout)
    data = _try_parse_json(retry_content)
    if data is not None:
        return data

    raise LLMError(
        "La réponse du modèle IA n'est pas un JSON valide, même après une nouvelle tentative."
    )
