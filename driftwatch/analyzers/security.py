from driftwatch.llm.provider import LLMProvider
from driftwatch.review.engine import ReviewContext
from driftwatch.review.models import CandidateFinding

SECURITY_PROMPT = """You are a security-focused code reviewer analyzing a single change from a GitHub pull request.

Repository: {repository}
Pull request: "{pr_title}"
{pr_body_section}

Changed {chunk_type} in `{file_path}` (lines {start_line}-{end_line}):
{imports_section}
```python
{code_text}
```

Look specifically for these categories of security issues, and ONLY report something if you see clear evidence of it in the code above:
- hard-coded secrets/credentials
- unsafe command execution (e.g. shell=True with untrusted input)
- SQL injection (string-built queries instead of parameterized queries)
- unsafe deserialization
- path traversal
- weak cryptographic usage
- insecure subprocess usage
- dangerous dynamic evaluation (eval/exec on untrusted input)

Rules:
- Only flag issues in the code shown above, not hypothetical code elsewhere.
- Do not invent files, functions, or line numbers that aren't shown above.
- start_line and end_line must fall within {start_line}-{end_line}.
- If you see no genuine issue, return an empty array.
- Be conservative: prefer no finding over a speculative one.
- confidence should reflect how certain you are that this is a real issue, not how severe it would be.

Respond with a JSON array of findings matching the required schema. Return [] if there are no genuine findings.
"""


def analyze(chunk: dict, repository: str, pr_title: str, pr_body: str, provider: LLMProvider) -> list[CandidateFinding]:
    pr_body_section = f'Description: "{pr_body}"' if pr_body else ""
    imports_section = f"Relevant imports:\n{chr(10).join(chunk['imports'])}\n" if chunk.get("imports") else ""

    prompt = SECURITY_PROMPT.format(
        repository=repository,
        pr_title=pr_title,
        pr_body_section=pr_body_section,
        chunk_type=chunk["type"],
        file_path=chunk["file"],
        start_line=chunk["start_line"],
        end_line=chunk["end_line"],
        imports_section=imports_section,
        code_text=chunk["text"],
    )

    findings = provider.generate_findings(prompt)
    return [f for f in findings if f.category == "security"]


class SecurityEngine:
    """ReviewEngine wrapper around analyze() (spec §14). The free function
    stays the direct entry point for anything that doesn't need the
    generic engine interface; this exists so orchestrator.analyze_and_decide
    can iterate over a list of engines instead of calling one hardcoded
    analyzer, ready for bug/quality engines to be added the same way later."""

    name = "security"

    def __init__(self, provider: LLMProvider):
        self._provider = provider

    def analyze(self, context: ReviewContext) -> list[CandidateFinding]:
        return analyze(context.chunk, context.repository, context.pr_title, context.pr_body, self._provider)
