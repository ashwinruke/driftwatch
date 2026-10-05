import driftwatch.persistence.evaluation_store as evaluation_store


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((" ".join(sql.split()), params))

    def fetchone(self):
        return (42,)

    def close(self):
        pass


class _FakeConn:
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        pass


def test_record_evaluation_run_stores_report_as_json_and_returns_id(monkeypatch):
    cursor = _FakeCursor()
    conn = _FakeConn(cursor)
    monkeypatch.setattr(evaluation_store, "get_connection", lambda: conn)

    run_id = evaluation_store.record_evaluation_run({"fixture_count": 10})

    assert run_id == 42
    assert conn.committed
    sql, params = cursor.executed[0]
    assert sql.startswith("INSERT INTO evaluation_runs")
    assert params[0].adapted == {"fixture_count": 10}
