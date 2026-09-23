CODE_FENCE = "```"


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
