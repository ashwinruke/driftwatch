import psycopg2
from pgvector.psycopg2 import register_vector

from driftwatch.app import config


def get_connection(register=True):
    conn = psycopg2.connect(config.DATABASE_URL)
    if register:
        register_vector(conn)
    return conn


def setup_schema():
    conn = psycopg2.connect(config.DATABASE_URL)
    cur = conn.cursor()

    cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
    conn.commit()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS doc_sections (
            id          SERIAL PRIMARY KEY,
            repo        TEXT NOT NULL,
            file_path   TEXT NOT NULL,
            heading     TEXT,
            content     TEXT NOT NULL,
            embedding   vector(768),
            indexed_at  TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS doc_sections_embedding_idx
        ON doc_sections
        USING ivfflat (embedding vector_cosine_ops)
        WITH (lists = 10);
    """)

    # Phase 6 (spec §28, trimmed -- see docs/roadmap.md's Phase 6 report):
    # dashboard-facing persistence for review runs/findings/evidence, which
    # nothing wrote to before this. `id` columns use TEXT rather than a
    # native UUID/SERIAL mix where a Python-generated id (Finding.id) is the
    # natural primary key, to avoid needing psycopg2 UUID adapter handling
    # for a one-time write.
    cur.execute("""
        CREATE TABLE IF NOT EXISTS repositories (
            id             SERIAL PRIMARY KEY,
            full_name      TEXT NOT NULL UNIQUE,
            owner          TEXT NOT NULL,
            name           TEXT NOT NULL,
            default_branch TEXT,
            created_at     TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS review_runs (
            id            SERIAL PRIMARY KEY,
            repository_id INTEGER NOT NULL REFERENCES repositories(id),
            pr_number     INTEGER NOT NULL,
            pr_title      TEXT,
            pr_author     TEXT,
            head_sha      TEXT,
            run_type      TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'running',
            error_message TEXT,
            started_at    TIMESTAMP DEFAULT NOW(),
            completed_at  TIMESTAMP
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS changed_chunks (
            id            SERIAL PRIMARY KEY,
            review_run_id INTEGER NOT NULL REFERENCES review_runs(id),
            file_path     TEXT NOT NULL,
            chunk_type    TEXT,
            chunk_name    TEXT,
            start_line    INTEGER,
            end_line      INTEGER
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS findings (
            id                 TEXT PRIMARY KEY,
            review_run_id      INTEGER NOT NULL REFERENCES review_runs(id),
            category           TEXT NOT NULL,
            severity           TEXT NOT NULL,
            title              TEXT NOT NULL,
            description        TEXT NOT NULL,
            file_path          TEXT NOT NULL,
            start_line         INTEGER NOT NULL,
            end_line           INTEGER NOT NULL,
            suggested_fix      TEXT,
            llm_confidence     REAL,
            validation_score   REAL,
            validation_status  TEXT NOT NULL,
            validation_reasons TEXT[],
            created_at         TIMESTAMP DEFAULT NOW()
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS evidence (
            id          SERIAL PRIMARY KEY,
            finding_id  TEXT NOT NULL REFERENCES findings(id),
            source      TEXT NOT NULL,
            description TEXT NOT NULL,
            file_path   TEXT,
            start_line  INTEGER,
            end_line    INTEGER,
            rule_id     TEXT
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS validation_results (
            finding_id                  TEXT PRIMARY KEY REFERENCES findings(id),
            diff_evidence_score         REAL,
            static_corroboration_score  REAL,
            ast_consistency_score       REAL,
            llm_confidence_score        REAL,
            final_score                 REAL NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            id                SERIAL PRIMARY KEY,
            review_run_id     INTEGER NOT NULL REFERENCES review_runs(id),
            finding_id        TEXT REFERENCES findings(id),
            comment_type      TEXT NOT NULL,
            github_comment_id BIGINT,
            github_url        TEXT,
            posted_at         TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()
    print("Schema ready.")


if __name__ == "__main__":
    setup_schema()
