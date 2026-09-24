from dataclasses import dataclass
from typing import Protocol

from driftwatch.review.models import CandidateFinding


@dataclass
class ReviewContext:
    """What a ReviewEngine needs to analyze one chunk. Deliberately generic
    (spec §14) -- engine-specific dependencies (an LLM provider, the doc
    index) stay internal to each engine rather than living here."""

    chunk: dict
    repository: str
    pull_request: int
    pr_title: str
    pr_body: str


class ReviewEngine(Protocol):
    name: str

    def analyze(self, context: ReviewContext) -> list[CandidateFinding]: ...
