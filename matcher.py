import logging
from embeddings import get_embedding
from db import get_connection

logger = logging.getLogger("driftwatch")

SIMILARITY_THRESHOLD = 0.50
TOP_K = 3


def find_stale_sections(repo: str, code_chunk: dict) -> list[dict]:
    text = f"{code_chunk['type']} {code_chunk['name']}\n{code_chunk['text']}"
    embedding = get_embedding(text)

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT
            file_path,
            heading,
            content,
            1 - (embedding <=> %s::vector) AS similarity
        FROM doc_sections
        WHERE repo = %s
        ORDER BY embedding <=> %s::vector
        LIMIT %s
    """, (embedding, repo, embedding, TOP_K))

    rows = cur.fetchall()
    logger.info(f"Top {len(rows)} candidate sections (all scores, for tuning):")
    for file_path, heading, content, similarity in rows:
        logger.info(f"    '{heading}' in {file_path} -> {similarity:.3f}")

    results = []
    for file_path, heading, content, similarity in rows:
        if similarity >= SIMILARITY_THRESHOLD:
            results.append({
                "file_path": file_path,
                "heading": heading,
                "content": content,
                "similarity": round(similarity, 3),
            })

    cur.close()
    conn.close()
    return results