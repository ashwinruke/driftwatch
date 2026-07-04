import logging
import httpx
from embeddings import get_embedding
from db import get_connection

logger = logging.getLogger("driftwatch")


def split_markdown_into_sections(content: str) -> list[dict]:
    """Split markdown into heading-level sections."""
    sections = []
    current_heading = None
    current_lines = []

    for line in content.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_lines).strip()
                })
            current_heading = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        sections.append({
            "heading": current_heading,
            "content": "\n".join(current_lines).strip()
        })

    return [s for s in sections if len(s["content"]) > 50]


def fetch_markdown_files(owner: str, repo: str, token: str, path: str = "") -> list[dict]:
    """Recursively fetch all .md files from a repo via GitHub API."""
    resp = httpx.get(
        f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
        headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
    )
    resp.raise_for_status()
    files = []
    for item in resp.json():
        if item["type"] == "file" and item["name"].endswith(".md"):
            files.append(item)
        elif item["type"] == "dir":
            files.extend(fetch_markdown_files(owner, repo, token, item["path"]))
    return files


def index_repo_docs(owner: str, repo: str, token: str):
    """Full index: fetch all markdown, split, embed, store."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM doc_sections WHERE repo = %s", (f"{owner}/{repo}",))

    md_files = fetch_markdown_files(owner, repo, token)
    logger.info(f"Found {len(md_files)} markdown files in {owner}/{repo}")

    for f in md_files:
        raw = httpx.get(
            f["download_url"],
            headers={"Authorization": f"Bearer {token}"},
        ).text

        sections = split_markdown_into_sections(raw)
        for section in sections:
            text_to_embed = f"{section['heading'] or ''}\n{section['content']}"
            embedding = get_embedding(text_to_embed)

            cur.execute("""
                INSERT INTO doc_sections (repo, file_path, heading, content, embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                f"{owner}/{repo}",
                f["path"],
                section["heading"],
                section["content"],
                embedding,
            ))
            logger.info(f"Indexed: {f['path']} -> '{section['heading']}'")

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Doc index complete for {owner}/{repo}")