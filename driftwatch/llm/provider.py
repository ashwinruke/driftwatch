import json
import logging
from typing import Protocol

import httpx
from google import genai
from google.genai import types

from driftwatch.app import config
from driftwatch.review.models import CandidateFinding

logger = logging.getLogger("driftwatch")


class LLMProvider(Protocol):
    def generate_findings(self, prompt: str) -> list[CandidateFinding]: ...


def parse_findings_response(raw_json: str) -> list[CandidateFinding]:
    """Parse a finding-list response into validated CandidateFindings.
    Accepts either a bare JSON array (Gemini's response_schema=list[...]
    enforces this shape) or {"findings": [...]} (Groq/OpenAI-compatible
    json_object mode doesn't enforce a schema, so the prompt asks for an
    object wrapper, which tends to be followed more reliably than a bare
    array). A malformed response, or a malformed individual item, is
    dropped with a warning rather than raised -- one bad LLM response
    shouldn't crash an entire review run."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("LLM response was not valid JSON, treating as no findings")
        return []

    if isinstance(data, dict):
        data = data.get("findings", [])

    findings = []
    for item in data:
        try:
            findings.append(CandidateFinding.model_validate(item))
        except Exception:
            logger.warning(f"Skipping malformed finding from LLM response: {item}")
    return findings


class GeminiProvider:
    def __init__(self, model: str = "gemini-2.5-flash"):
        self._client = genai.Client(api_key=config.GEMINI_API_KEY)
        self._model = model

    def generate_findings(self, prompt: str) -> list[CandidateFinding]:
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=list[CandidateFinding],
            ),
        )
        return parse_findings_response(response.text)


_CANDIDATE_FINDING_SCHEMA = json.dumps(CandidateFinding.model_json_schema())

_FINDINGS_SCHEMA_HINT = (
    '\n\nRespond with a JSON object of exactly this shape: {"findings": [<array of '
    'finding objects>]} -- use {"findings": []} if there are none. Each finding '
    f"object must match this JSON schema:\n{_CANDIDATE_FINDING_SCHEMA}"
)


class GroqProvider:
    """Talks to Groq's OpenAI-compatible chat completions API directly via
    httpx, rather than adding the groq/openai SDK as a dependency for what
    is otherwise a single JSON POST request."""

    API_URL = "https://api.groq.com/openai/v1/chat/completions"
    TIMEOUT_SECONDS = 30

    def __init__(self, model: str | None = None):
        self._model = model or config.GROQ_MODEL

    def generate_findings(self, prompt: str) -> list[CandidateFinding]:
        response = httpx.post(
            self.API_URL,
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={
                "model": self._model,
                "messages": [{"role": "user", "content": prompt + _FINDINGS_SCHEMA_HINT}],
                "response_format": {"type": "json_object"},
            },
            timeout=self.TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return parse_findings_response(content)


class FallbackProvider:
    """Tries `primary`; if it raises anything, logs a warning and tries
    `fallback` instead. Provider-agnostic on purpose -- doesn't know or
    care what `primary`/`fallback` actually are, just that both implement
    LLMProvider. If both fail, the fallback's exception propagates."""

    def __init__(self, primary: LLMProvider, fallback: LLMProvider):
        self._primary = primary
        self._fallback = fallback

    def generate_findings(self, prompt: str) -> list[CandidateFinding]:
        try:
            return self._primary.generate_findings(prompt)
        except Exception as e:
            logger.warning(f"Primary LLM provider failed ({e}), falling back")
            return self._fallback.generate_findings(prompt)
