import json
import logging
from typing import Protocol

from google import genai
from google.genai import types

from driftwatch.app import config
from driftwatch.review.models import CandidateFinding

logger = logging.getLogger("driftwatch")


class LLMProvider(Protocol):
    def generate_findings(self, prompt: str) -> list[CandidateFinding]: ...


def parse_findings_response(raw_json: str) -> list[CandidateFinding]:
    """Parse a JSON array of finding objects into validated CandidateFindings.
    A malformed response (or a malformed individual item) is dropped with a
    warning rather than raised, since one bad LLM response shouldn't crash
    an entire review run."""
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning("LLM response was not valid JSON, treating as no findings")
        return []

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
