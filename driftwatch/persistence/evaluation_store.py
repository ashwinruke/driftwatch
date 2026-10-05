from psycopg2.extras import Json

from driftwatch.persistence.db import get_connection


def record_evaluation_run(report: dict) -> int:
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO evaluation_runs (report) VALUES (%s) RETURNING id", (Json(report),))
    run_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return run_id
