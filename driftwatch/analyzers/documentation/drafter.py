from google import genai

from driftwatch.app import config
from driftwatch.observability.tracing import traced_generation

_client = genai.Client(api_key=config.GEMINI_API_KEY)

DRAFT_PROMPT = """You are reviewing a documentation section that may be outdated because related code changed.

Changed code ({chunk_type} '{chunk_name}' in {file}):
{code_text}

Current documentation section ("{heading}" in {doc_file}):
{doc_content}

Task: Determine if the documentation is actually outdated given the code change. If it looks outdated, draft a concise, corrected version of ONLY this section's content — do not include any surrounding text, other sections, or content that wasn't part of the original section shown above. If the code change does not actually affect what this section describes, say so plainly instead of forcing an edit.

Respond in exactly this format:
VERDICT: OUTDATED or NOT_OUTDATED
DRAFT: the corrected section text, or N/A if not outdated
REASON: one sentence explaining your verdict
"""


@traced_generation("gemini-draft-update")
def draft_update(code_chunk: dict, doc_section: dict) -> dict:
    prompt = DRAFT_PROMPT.format(
        chunk_type=code_chunk["type"],
        chunk_name=code_chunk["name"],
        file=code_chunk["file"],
        code_text=code_chunk["text"],
        heading=doc_section["heading"],
        doc_file=doc_section["file_path"],
        doc_content=doc_section["content"],
    )

    response = _client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()

    verdict = "UNKNOWN"
    draft_lines = []
    reason_lines = []
    mode = None

    for line in text.splitlines():
        if line.startswith("VERDICT:"):
            verdict = line.split("VERDICT:", 1)[1].strip()
            mode = None
        elif line.startswith("DRAFT:"):
            first = line.split("DRAFT:", 1)[1].strip()
            draft_lines = [first] if first else []
            mode = "draft"
        elif line.startswith("REASON:"):
            first = line.split("REASON:", 1)[1].strip()
            reason_lines = [first] if first else []
            mode = "reason"
        elif mode == "draft":
            draft_lines.append(line)
        elif mode == "reason":
            reason_lines.append(line)

    draft = "\n".join(draft_lines).strip()
    reason = " ".join(reason_lines).strip()

    return {"verdict": verdict, "draft": draft, "reason": reason, "raw": text}
