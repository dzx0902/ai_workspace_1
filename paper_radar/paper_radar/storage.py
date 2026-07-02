from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .models import Paper
from .utils import DB_PATH

_JSON_FIELDS = {"authors", "matched_keywords", "llm_category"}


class PaperStorage:
    def __init__(self, db_path: str | Path = DB_PATH):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def init_db(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS papers (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    external_id TEXT NOT NULL DEFAULT '',
                    authors TEXT NOT NULL DEFAULT '[]',
                    summary TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL,
                    source_category TEXT NOT NULL DEFAULT '',
                    url TEXT NOT NULL UNIQUE,
                    pdf_url TEXT NOT NULL DEFAULT '',
                    published TEXT NOT NULL DEFAULT '',
                    fetched_at TEXT NOT NULL,
                    rule_score INTEGER,
                    matched_keywords TEXT NOT NULL DEFAULT '[]',
                    llm_score REAL,
                    llm_category TEXT NOT NULL DEFAULT '[]',
                    llm_decision TEXT NOT NULL DEFAULT '',
                    llm_reason TEXT NOT NULL DEFAULT '',
                    note_priority TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'fetched',
                    llm_error TEXT NOT NULL DEFAULT '',
                    pdf_path TEXT NOT NULL DEFAULT '',
                    pdf_download_status TEXT NOT NULL DEFAULT '',
                    pdf_download_error TEXT NOT NULL DEFAULT '',
                    extracted_text_path TEXT NOT NULL DEFAULT '',
                    pdf_extract_status TEXT NOT NULL DEFAULT '',
                    pdf_extract_error TEXT NOT NULL DEFAULT '',
                    paper_note_path TEXT NOT NULL DEFAULT '',
                    full_summary_status TEXT NOT NULL DEFAULT '',
                    full_summary_error TEXT NOT NULL DEFAULT '',
                    feedback_relevant INTEGER NOT NULL DEFAULT 0,
                    feedback_not_relevant INTEGER NOT NULL DEFAULT 0,
                    feedback_read_later INTEGER NOT NULL DEFAULT 0,
                    feedback_related_work INTEGER NOT NULL DEFAULT 0,
                    feedback_summarize INTEGER NOT NULL DEFAULT 0
                );
                CREATE TABLE IF NOT EXISTS llm_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    paper_id TEXT NOT NULL DEFAULT '',
                    purpose TEXT NOT NULL,
                    provider TEXT NOT NULL DEFAULT '',
                    model TEXT NOT NULL DEFAULT '',
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost REAL NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_papers_status ON papers(status);
                CREATE INDEX IF NOT EXISTS idx_papers_fetched_at ON papers(fetched_at);
                CREATE INDEX IF NOT EXISTS idx_papers_published ON papers(published);
                """
            )
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(papers)").fetchall()
            }
            if "external_id" not in columns:
                connection.execute(
                    "ALTER TABLE papers ADD COLUMN external_id TEXT NOT NULL DEFAULT ''"
                )
                connection.execute(
                    "UPDATE papers SET external_id = id WHERE external_id = ''"
                )
            migrations = {
                "pdf_path": "TEXT NOT NULL DEFAULT ''",
                "pdf_download_status": "TEXT NOT NULL DEFAULT ''",
                "pdf_download_error": "TEXT NOT NULL DEFAULT ''",
                "extracted_text_path": "TEXT NOT NULL DEFAULT ''",
                "pdf_extract_status": "TEXT NOT NULL DEFAULT ''",
                "pdf_extract_error": "TEXT NOT NULL DEFAULT ''",
                "paper_note_path": "TEXT NOT NULL DEFAULT ''",
                "full_summary_status": "TEXT NOT NULL DEFAULT ''",
                "full_summary_error": "TEXT NOT NULL DEFAULT ''",
                "feedback_relevant": "INTEGER NOT NULL DEFAULT 0",
                "feedback_not_relevant": "INTEGER NOT NULL DEFAULT 0",
                "feedback_read_later": "INTEGER NOT NULL DEFAULT 0",
                "feedback_related_work": "INTEGER NOT NULL DEFAULT 0",
                "feedback_summarize": "INTEGER NOT NULL DEFAULT 0",
            }
            for column, definition in migrations.items():
                if column not in columns:
                    connection.execute(
                        f"ALTER TABLE papers ADD COLUMN {column} {definition}"
                    )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_papers_external_id
                ON papers(source, external_id)
                """
            )

    @staticmethod
    def _encode(value: Any) -> str:
        return json.dumps(value, ensure_ascii=False)

    @classmethod
    def _paper_from_row(cls, row: sqlite3.Row) -> Paper:
        values = dict(row)
        for field in _JSON_FIELDS:
            raw = values.get(field) or "[]"
            try:
                values[field] = json.loads(raw)
            except (TypeError, json.JSONDecodeError):
                values[field] = []
        return Paper(**values)

    def upsert_paper(self, paper: Paper) -> bool:
        with self.connect() as connection:
            existing = connection.execute(
                "SELECT id FROM papers WHERE id = ? OR url = ?",
                (paper.id, paper.url),
            ).fetchone()
            if existing:
                connection.execute(
                    """
                    UPDATE papers
                    SET title = ?, external_id = ?, authors = ?, summary = ?, source = ?,
                        source_category = ?, url = ?, pdf_url = ?, published = ?
                    WHERE id = ?
                    """,
                    (
                        paper.title,
                        paper.external_id or paper.id,
                        self._encode(paper.authors),
                        paper.summary,
                        paper.source,
                        paper.source_category,
                        paper.url,
                        paper.pdf_url,
                        paper.published,
                        existing["id"],
                    ),
                )
                return False
            connection.execute(
                """
                INSERT INTO papers (
                    id, title, external_id, authors, summary, source, source_category, url,
                    pdf_url, published, fetched_at, rule_score, matched_keywords,
                    llm_score, llm_category, llm_decision, llm_reason,
                    note_priority, status, llm_error
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper.id,
                    paper.title,
                    paper.external_id or paper.id,
                    self._encode(paper.authors),
                    paper.summary,
                    paper.source,
                    paper.source_category,
                    paper.url,
                    paper.pdf_url,
                    paper.published,
                    paper.fetched_at,
                    paper.rule_score,
                    self._encode(paper.matched_keywords),
                    paper.llm_score,
                    self._encode(paper.llm_category),
                    paper.llm_decision,
                    paper.llm_reason,
                    paper.note_priority,
                    paper.status,
                    paper.llm_error,
                ),
            )
            return True

    def get_by_status(self, status: str, limit: int | None = None) -> list[Paper]:
        sql = "SELECT * FROM papers WHERE status = ? ORDER BY fetched_at, id"
        params: list[Any] = [status]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            return [self._paper_from_row(row) for row in connection.execute(sql, params)]

    def get_unfiltered(self) -> list[Paper]:
        return self.get_by_status("fetched")

    def get_llm_pending(
        self,
        limit: int | None = None,
        date: str | None = None,
    ) -> list[Paper]:
        sql = "SELECT * FROM papers WHERE status = 'llm_pending'"
        params: list[Any] = []
        if date:
            sql += " AND substr(fetched_at, 1, 10) = ?"
            params.append(date)
        sql += " ORDER BY COALESCE(rule_score, 0) DESC, fetched_at, id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            return [self._paper_from_row(row) for row in connection.execute(sql, params)]

    def get_paper(self, paper_id: str) -> Paper | None:
        normalized = paper_id.strip()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM papers WHERE id = ? OR id = ?",
                (normalized, normalized.removesuffix(".pdf")),
            ).fetchone()
            return self._paper_from_row(row) if row else None

    def update_rule_result(
        self,
        paper_id: str,
        score: int,
        matches: list[dict[str, Any]],
        status: str,
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET rule_score = ?, matched_keywords = ?, status = ?
                WHERE id = ?
                """,
                (score, self._encode(matches), status, paper_id),
            )

    def update_llm_result(self, paper_id: str, result: dict[str, Any]) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET llm_score = ?, llm_category = ?, llm_decision = ?,
                    llm_reason = ?, note_priority = ?, status = 'scored',
                    llm_error = ''
                WHERE id = ?
                """,
                (
                    result["relevance_score"],
                    self._encode(result["category"]),
                    result["decision"],
                    result["reason"],
                    result["note_priority"],
                    paper_id,
                ),
            )

    def mark_llm_failed(self, paper_id: str, error: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE papers SET status = 'llm_failed', llm_error = ? WHERE id = ?",
                (error[:1000], paper_id),
            )

    def get_candidates_for_date(self, date: str) -> list[Paper]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM papers
                WHERE substr(fetched_at, 1, 10) = ?
                ORDER BY COALESCE(llm_score, rule_score, 0) DESC, title
                """,
                (date,),
            )
            return [self._paper_from_row(row) for row in rows]

    def count_for_date(self, date: str, statuses: Iterable[str] | None = None) -> int:
        sql = "SELECT COUNT(*) FROM papers WHERE substr(fetched_at, 1, 10) = ?"
        params: list[Any] = [date]
        if statuses:
            status_list = list(statuses)
            sql += f" AND status IN ({','.join('?' for _ in status_list)})"
            params.extend(status_list)
        with self.connect() as connection:
            return int(connection.execute(sql, params).fetchone()[0])

    def get_pdf_candidates(
        self,
        min_llm_score: float,
        allowed_sources: Iterable[str],
        limit: int | None = None,
        date: str | None = None,
    ) -> list[Paper]:
        sources = list(allowed_sources)
        if not sources:
            return []
        sql = f"""
            SELECT * FROM papers
            WHERE source IN ({','.join('?' for _ in sources)})
              AND llm_score >= ?
              AND (llm_decision = 'read' OR note_priority = 'high')
              AND pdf_download_status != 'downloaded'
        """
        params: list[Any] = [*sources, min_llm_score]
        if date:
            sql += " AND substr(fetched_at, 1, 10) = ?"
            params.append(date)
        sql += " ORDER BY llm_score DESC, published DESC, id"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            return [self._paper_from_row(row) for row in connection.execute(sql, params)]

    def get_extract_candidates(self, limit: int | None = None) -> list[Paper]:
        sql = """
            SELECT * FROM papers
            WHERE pdf_download_status = 'downloaded'
              AND pdf_path != ''
              AND pdf_extract_status != 'extracted'
            ORDER BY llm_score DESC, id
        """
        params: list[Any] = []
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            return [self._paper_from_row(row) for row in connection.execute(sql, params)]

    def get_summary_candidates(
        self,
        date: str,
        limit: int | None = None,
    ) -> list[Paper]:
        sql = """
            SELECT * FROM papers
            WHERE substr(fetched_at, 1, 10) = ?
              AND (llm_decision = 'read' OR note_priority = 'high')
              AND pdf_extract_status = 'extracted'
              AND extracted_text_path != ''
              AND full_summary_status != 'summarized'
            ORDER BY llm_score DESC, id
        """
        params: list[Any] = [date]
        if limit is not None:
            sql += " LIMIT ?"
            params.append(limit)
        with self.connect() as connection:
            return [self._paper_from_row(row) for row in connection.execute(sql, params)]

    def update_pdf_download(
        self,
        paper_id: str,
        status: str,
        path: str = "",
        error: str = "",
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET pdf_path = ?, pdf_download_status = ?, pdf_download_error = ?
                WHERE id = ?
                """,
                (path, status, error[:1000], paper_id),
            )

    def update_pdf_extract(
        self,
        paper_id: str,
        status: str,
        path: str = "",
        error: str = "",
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET extracted_text_path = ?, pdf_extract_status = ?,
                    pdf_extract_error = ?
                WHERE id = ?
                """,
                (path, status, error[:1000], paper_id),
            )

    def update_full_summary(
        self,
        paper_id: str,
        status: str,
        note_path: str = "",
        error: str = "",
    ) -> None:
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE papers
                SET paper_note_path = ?, full_summary_status = ?,
                    full_summary_error = ?
                WHERE id = ?
                """,
                (note_path, status, error[:1000], paper_id),
            )

    def get_papers_between(self, start_date: str, end_date: str) -> list[Paper]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM papers
                WHERE substr(fetched_at, 1, 10) BETWEEN ? AND ?
                ORDER BY COALESCE(llm_score, rule_score, 0) DESC, published DESC
                """,
                (start_date, end_date),
            )
            return [self._paper_from_row(row) for row in rows]

    def update_feedback(self, paper_id: str, feedback: dict[str, bool]) -> None:
        fields = {
            "relevant": "feedback_relevant",
            "not_relevant": "feedback_not_relevant",
            "read_later": "feedback_read_later",
            "related_work": "feedback_related_work",
            "summarize": "feedback_summarize",
        }
        assignments = ", ".join(f"{column} = ?" for column in fields.values())
        values = [int(bool(feedback.get(key))) for key in fields]
        with self.connect() as connection:
            connection.execute(
                f"UPDATE papers SET {assignments} WHERE id = ?",
                (*values, paper_id),
            )

    def get_feedback_papers(self) -> list[Paper]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM papers
                WHERE feedback_relevant = 1 OR feedback_not_relevant = 1
                   OR feedback_read_later = 1 OR feedback_related_work = 1
                   OR feedback_summarize = 1
                """
            )
            return [self._paper_from_row(row) for row in rows]

    def record_llm_usage(
        self,
        paper_id: str,
        purpose: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        estimated_cost: float = 0,
    ) -> None:
        from .utils import now_iso

        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO llm_usage (
                    paper_id, purpose, provider, model, prompt_tokens,
                    completion_tokens, estimated_cost, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    paper_id,
                    purpose,
                    provider,
                    model,
                    prompt_tokens,
                    completion_tokens,
                    estimated_cost,
                    now_iso(),
                ),
            )

    def llm_usage_summary(self, date_prefix: str | None = None) -> dict[str, float]:
        sql = """
            SELECT COUNT(*), COALESCE(SUM(prompt_tokens), 0),
                   COALESCE(SUM(completion_tokens), 0),
                   COALESCE(SUM(estimated_cost), 0)
            FROM llm_usage
        """
        params: tuple[str, ...] = ()
        if date_prefix:
            sql += " WHERE substr(created_at, 1, 10) = ?"
            params = (date_prefix,)
        with self.connect() as connection:
            row = connection.execute(sql, params).fetchone()
        return {
            "calls": int(row[0]),
            "prompt_tokens": int(row[1]),
            "completion_tokens": int(row[2]),
            "estimated_cost": float(row[3]),
        }
