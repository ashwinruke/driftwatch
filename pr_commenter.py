import httpx

CODE_FENCE = "```"


def post_pr_comment(owner: str, repo: str, pr_number: int, token: str, body: str):
    resp = httpx.post(
        f"https://api.github.com/repos/{owner}/{repo}/issues/{pr_number}/comments",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        json={"body": body},
    )
    resp.raise_for_status()
    return resp.json()


def format_drift_comment(chunk: dict, doc_section: dict, draft_result: dict) -> str:
    return (
        f"**Possible documentation drift detected**\n\n"
        f"Changed: `{chunk['type']} {chunk['name']}` in `{chunk['file']}` "
        f"(lines {chunk['start_line']}-{chunk['end_line']})\n"
        f"Related doc section: **{doc_section['heading']}** in `{doc_section['file_path']}` "
        f"(similarity: {doc_section['similarity']})\n\n"
        f"**Assessment:** {draft_result['reason']}\n\n"
        f"**Suggested update:**\n\n"
        f"{CODE_FENCE}\n{draft_result['draft']}\n{CODE_FENCE}\n\n"
        f"---\n"
        f"*Posted automatically by DriftWatch. This is a suggestion, not an automatic edit — please review before applying.*"
    )