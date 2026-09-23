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

    conn.commit()
    cur.close()
    conn.close()
    print("Schema ready.")


if __name__ == "__main__":
    setup_schema()
