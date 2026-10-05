import driftwatch.analyzers.documentation.indexer as indexer


class _FakeCursor:
    def __init__(self, docs_indexed_at):
        self._docs_indexed_at = docs_indexed_at
        self.executed: list[tuple[str, tuple | None]] = []
        self._last_sql = ""

    def execute(self, sql, params=None):
        self._last_sql = " ".join(sql.split())
        self.executed.append((self._last_sql, params))

    def fetchone(self):
        if self._last_sql.startswith("SELECT docs_indexed_at"):
            return (self._docs_indexed_at,)
        return None

    def close(self):
        pass

    def sql_statements(self) -> list[str]:
        return [sql for sql, _ in self.executed]


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


def _install_fake_db(monkeypatch, docs_indexed_at) -> _FakeCursor:
    cursor = _FakeCursor(docs_indexed_at)
    monkeypatch.setattr(indexer, "get_connection", lambda: _FakeConn(cursor))
    return cursor


def test_skips_indexing_when_repo_already_indexed(monkeypatch):
    cursor = _install_fake_db(monkeypatch, docs_indexed_at="2026-10-01 12:00:00")
    fetched = []
    monkeypatch.setattr(indexer, "fetch_markdown_files", lambda *a, **k: fetched.append(a) or [])

    indexer.index_repo_docs("o", "r", "tok", only_if_unindexed=True)

    assert fetched == []
    assert not any(sql.startswith("DELETE FROM doc_sections") for sql in cursor.sql_statements())


def test_indexes_and_stamps_when_repo_never_indexed(monkeypatch):
    cursor = _install_fake_db(monkeypatch, docs_indexed_at=None)
    monkeypatch.setattr(indexer, "fetch_markdown_files", lambda *a, **k: [])

    indexer.index_repo_docs("o", "r", "tok", only_if_unindexed=True)

    statements = cursor.sql_statements()
    assert any(sql.startswith("DELETE FROM doc_sections") for sql in statements)
    assert any(sql.startswith("UPDATE repositories SET docs_indexed_at") for sql in statements)


def test_full_rebuild_ignores_existing_stamp(monkeypatch):
    # index_now.py's manual rebuild must still run even if the repo is stamped.
    cursor = _install_fake_db(monkeypatch, docs_indexed_at="2026-10-01 12:00:00")
    monkeypatch.setattr(indexer, "fetch_markdown_files", lambda *a, **k: [])

    indexer.index_repo_docs("o", "r", "tok")

    assert any(sql.startswith("DELETE FROM doc_sections") for sql in cursor.sql_statements())
