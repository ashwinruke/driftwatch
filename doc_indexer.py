import logging
import httpx
from embeddings import get_embedding
from db import get_connection
from embeddings import get_embedding

logger = logging.getLogger("driftwatch")


def split_markdown_into_sections(content: str) -> list[dict]:
    """Split markdown into heading-level sections, then further into paragraph-level chunks."""
    raw_sections = []
    current_heading = None
    current_lines = []

    for line in content.splitlines():
        if line.startswith("#"):
            if current_lines:
                raw_sections.append({
                    "heading": current_heading,
                    "content": "\n".join(current_lines).strip()
                })
            current_heading = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    if current_lines:
        raw_sections.append({
            "heading": current_heading,
            "content": "\n".join(current_lines).strip()
        })

    # Now split each raw section further into paragraph-level chunks,
    # so a single heading with multiple unrelated paragraphs doesn't
    # get embedded and matched as one oversized block.
    final_sections = []
    for section in raw_sections:
        paragraphs = _split_into_paragraphs(section["content"])
        for para in paragraphs:
            if len(para.strip()) > 50:
                final_sections.append({
                    "heading": section["heading"],
                    "content": para.strip(),
                })

    return final_sections


def _split_into_paragraphs(content: str) -> list[str]:
    """Split content into paragraphs, keeping fenced code blocks intact as single units."""
    paragraphs = []
    current = []
    in_code_block = False

    for line in content.splitlines():
        if line.strip().startswith("```"):
            if not in_code_block:
                # Opening a code fence: if we already have accumulated
                # text before it, that's its own paragraph.
                if current:
                    paragraphs.append("\n".join(current))
                    current = []
                current.append(line)
                in_code_block = True
            else:
                # Closing a code fence: the code block itself is
                # its own paragraph, flush it immediately.
                current.append(line)
                paragraphs.append("\n".join(current))
                current = []
                in_code_block = False
            continue

        if not in_code_block and line.strip() == "":
            if current:
                paragraphs.append("\n".join(current))
                current = []
        else:
            current.append(line)

    if current:
        paragraphs.append("\n".join(current))

    return paragraphs


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

def remove_file_from_index(repo: str, file_path: str):
    """Remove all indexed sections for a specific file (e.g. when it's deleted)."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM doc_sections WHERE repo = %s AND file_path = %s",
        (repo, file_path)
    )
    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Removed indexed sections for deleted file: {file_path}")


def index_specific_files(owner: str, repo: str, token: str, added_or_modified: list[str], removed: list[str]):
    """Re-index only the specific files that changed, instead of rebuilding the whole repo's index."""
    repo_full = f"{owner}/{repo}"
    conn = get_connection()
    cur = conn.cursor()

    for file_path in removed:
        cur.execute(
            "DELETE FROM doc_sections WHERE repo = %s AND file_path = %s",
            (repo_full, file_path)
        )
        logger.info(f"Removed indexed sections for deleted file: {file_path}")

    for file_path in added_or_modified:
        # Clear any existing sections for this file first (in case it was modified, not just added)
        cur.execute(
            "DELETE FROM doc_sections WHERE repo = %s AND file_path = %s",
            (repo_full, file_path)
        )

        resp = httpx.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}",
            headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"},
        )
        if resp.status_code == 404:
            # File was in the push payload but no longer exists at HEAD (rare edge case)
            logger.info(f"Skipping {file_path}: not found at current HEAD")
            continue
        resp.raise_for_status()

        download_url = resp.json().get("download_url")
        if not download_url:
            logger.info(f"Skipping {file_path}: no download URL (possibly a directory or symlink)")
            continue

        raw = httpx.get(download_url, headers={"Authorization": f"Bearer {token}"}).text
        sections = split_markdown_into_sections(raw)

        for section in sections:
            text_to_embed = f"{section['heading'] or ''}\n{section['content']}"
            embedding = get_embedding(text_to_embed)

            cur.execute("""
                INSERT INTO doc_sections (repo, file_path, heading, content, embedding)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                repo_full,
                file_path,
                section["heading"],
                section["content"],
                embedding,
            ))
            logger.info(f"Re-indexed: {file_path} -> '{section['heading']}'")

    conn.commit()
    cur.close()
    conn.close()
    logger.info(f"Incremental re-index complete for {repo_full}: {len(added_or_modified)} updated, {len(removed)} removed")