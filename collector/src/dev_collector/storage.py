"""SQLite storage layer for OTLP telemetry data."""

from __future__ import annotations

import json
import os
import time

import aiosqlite

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "..", "..", ".dev-collector.db")
DEFAULT_RETAIN_MINUTES = 60


def _safe_json_loads(value: str, default):
    """Parse JSON with a fallback for corrupted data."""
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return default

_CREATE_SPANS = """
CREATE TABLE IF NOT EXISTS spans (
    trace_id TEXT NOT NULL,
    span_id TEXT NOT NULL,
    parent_span_id TEXT DEFAULT '',
    name TEXT NOT NULL,
    service_name TEXT DEFAULT '',
    kind INTEGER DEFAULT 0,
    status INTEGER DEFAULT 0,
    start_time_unix_nano INTEGER NOT NULL,
    end_time_unix_nano INTEGER NOT NULL,
    duration_ms REAL DEFAULT 0.0,
    attributes TEXT DEFAULT '{}',
    events TEXT DEFAULT '[]',
    PRIMARY KEY (trace_id, span_id)
);
"""

_CREATE_LOGS = """
CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_unix_nano INTEGER NOT NULL,
    trace_id TEXT DEFAULT '',
    span_id TEXT DEFAULT '',
    severity_number INTEGER DEFAULT 0,
    severity_text TEXT DEFAULT '',
    body TEXT DEFAULT '',
    attributes TEXT DEFAULT '{}',
    resource_attributes TEXT DEFAULT '{}',
    service_name TEXT DEFAULT ''
);
"""

_CREATE_METRICS = """
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp_unix_nano INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT DEFAULT '',
    unit TEXT DEFAULT '',
    type TEXT DEFAULT '',
    value REAL DEFAULT 0.0,
    attributes TEXT DEFAULT '{}',
    resource_attributes TEXT DEFAULT '{}',
    service_name TEXT DEFAULT '',
    exemplar_trace_id TEXT DEFAULT '',
    exemplar_span_id TEXT DEFAULT ''
);
"""

_CREATE_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_spans_trace ON spans(trace_id);",
    "CREATE INDEX IF NOT EXISTS idx_spans_service ON spans(service_name);",
    "CREATE INDEX IF NOT EXISTS idx_spans_start ON spans(start_time_unix_nano);",
    "CREATE INDEX IF NOT EXISTS idx_logs_trace ON logs(trace_id);",
    "CREATE INDEX IF NOT EXISTS idx_logs_span ON logs(span_id);",
    "CREATE INDEX IF NOT EXISTS idx_logs_service ON logs(service_name);",
    "CREATE INDEX IF NOT EXISTS idx_logs_ts ON logs(timestamp_unix_nano);",
    "CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(name);",
    "CREATE INDEX IF NOT EXISTS idx_metrics_service ON metrics(service_name);",
    "CREATE INDEX IF NOT EXISTS idx_metrics_ts ON metrics(timestamp_unix_nano);",
]


class Storage:
    """Async SQLite storage for OTLP telemetry data."""

    def __init__(self, db_path: str = DEFAULT_DB_PATH) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the database and create tables."""
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.execute("PRAGMA journal_mode=WAL;")
        await self._db.execute(_CREATE_SPANS)
        await self._db.execute(_CREATE_LOGS)
        await self._db.execute(_CREATE_METRICS)
        for idx_sql in _CREATE_INDEXES:
            await self._db.execute(idx_sql)
        await self._db.commit()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    @property
    def db(self) -> aiosqlite.Connection:
        """Return the active database connection."""
        if self._db is None:
            raise RuntimeError("Storage is not connected")
        return self._db

    # ── Inserts ──────────────────────────────────────────────

    async def insert_spans(self, spans: list[dict]) -> int:
        """Insert span records. Returns count inserted."""
        if not spans:
            return 0
        await self.db.executemany(
            """INSERT OR REPLACE INTO spans
               (trace_id, span_id, parent_span_id, name, service_name,
                kind, status, start_time_unix_nano, end_time_unix_nano,
                duration_ms, attributes, events)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    s["trace_id"],
                    s["span_id"],
                    s.get("parent_span_id", ""),
                    s["name"],
                    s.get("service_name", ""),
                    s.get("kind", 0),
                    s.get("status", 0),
                    s["start_time_unix_nano"],
                    s["end_time_unix_nano"],
                    s.get("duration_ms", 0.0),
                    json.dumps(s.get("attributes", {})),
                    json.dumps(s.get("events", [])),
                )
                for s in spans
            ],
        )
        await self.db.commit()
        return len(spans)

    async def insert_logs(self, logs: list[dict]) -> int:
        """Insert log records. Returns count inserted."""
        if not logs:
            return 0
        await self.db.executemany(
            """INSERT INTO logs
               (timestamp_unix_nano, trace_id, span_id, severity_number,
                severity_text, body, attributes, resource_attributes, service_name)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    lg["timestamp_unix_nano"],
                    lg.get("trace_id", ""),
                    lg.get("span_id", ""),
                    lg.get("severity_number", 0),
                    lg.get("severity_text", ""),
                    lg.get("body", ""),
                    json.dumps(lg.get("attributes", {})),
                    json.dumps(lg.get("resource_attributes", {})),
                    lg.get("service_name", ""),
                )
                for lg in logs
            ],
        )
        await self.db.commit()
        return len(logs)

    async def insert_metrics(self, metrics: list[dict]) -> int:
        """Insert metric records. Returns count inserted."""
        if not metrics:
            return 0
        await self.db.executemany(
            """INSERT INTO metrics
               (timestamp_unix_nano, name, description, unit, type, value,
                attributes, resource_attributes, service_name,
                exemplar_trace_id, exemplar_span_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    m["timestamp_unix_nano"],
                    m["name"],
                    m.get("description", ""),
                    m.get("unit", ""),
                    m.get("type", ""),
                    m.get("value", 0.0),
                    json.dumps(m.get("attributes", {})),
                    json.dumps(m.get("resource_attributes", {})),
                    m.get("service_name", ""),
                    m.get("exemplar_trace_id", ""),
                    m.get("exemplar_span_id", ""),
                )
                for m in metrics
            ],
        )
        await self.db.commit()
        return len(metrics)

    # ── Queries ──────────────────────────────────────────────

    async def get_services(self) -> list[str]:
        """Return distinct service names across all signal types."""
        services: set[str] = set()
        for table in ("spans", "logs", "metrics"):
            cursor = await self.db.execute(
                f"SELECT DISTINCT service_name FROM {table} WHERE service_name != ''"  # noqa: S608
            )
            rows = await cursor.fetchall()
            services.update(row[0] for row in rows)
        return sorted(services)

    async def get_traces(
        self,
        service: str | None = None,
        since_ns: int | None = None,
        limit: int = 50,
    ) -> list[dict]:
        """Return recent traces grouped by trace_id with summary info."""
        conditions: list[str] = []
        params: list = []
        if service:
            conditions.append("service_name = ?")
            params.append(service)
        if since_ns is not None:
            conditions.append("start_time_unix_nano >= ?")
            params.append(since_ns)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        # Use a subquery to find the real root span (no parent) per trace,
        # then join back for accurate root_span_name and service_name.
        query = f"""
            SELECT g.trace_id,
                   COALESCE(root.name, g.first_name) as root_span_name,
                   COALESCE(root.service_name, g.first_service) as service_name,
                   g.start_time_unix_nano,
                   g.duration_ns,
                   g.span_count
            FROM (
                SELECT trace_id,
                       MIN(name) as first_name,
                       MIN(service_name) as first_service,
                       MIN(start_time_unix_nano) as start_time_unix_nano,
                       MAX(end_time_unix_nano) - MIN(start_time_unix_nano) as duration_ns,
                       COUNT(*) as span_count
                FROM spans
                {where}
                GROUP BY trace_id
            ) g
            LEFT JOIN spans root
                ON root.trace_id = g.trace_id AND root.parent_span_id = ''
            ORDER BY g.start_time_unix_nano DESC
            LIMIT ?
        """  # noqa: S608
        params.append(limit)
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "trace_id": row[0],
                "root_span_name": row[1] or "",
                "service_name": row[2] or "",
                "start_time_unix_nano": row[3],
                "duration_ms": (row[4] or 0) / 1_000_000,
                "span_count": row[5],
            }
            for row in rows
        ]

    async def get_trace_spans(self, trace_id: str) -> list[dict]:
        """Return all spans for a given trace_id."""
        cursor = await self.db.execute(
            """SELECT trace_id, span_id, parent_span_id, name, service_name,
                      kind, status, start_time_unix_nano, end_time_unix_nano,
                      duration_ms, attributes, events
               FROM spans WHERE trace_id = ?
               ORDER BY start_time_unix_nano""",
            (trace_id,),
        )
        rows = await cursor.fetchall()
        return [
            {
                "trace_id": row[0],
                "span_id": row[1],
                "parent_span_id": row[2],
                "name": row[3],
                "service_name": row[4],
                "kind": row[5],
                "status": row[6],
                "start_time_unix_nano": row[7],
                "end_time_unix_nano": row[8],
                "duration_ms": row[9],
                "attributes": _safe_json_loads(row[10], {}),
                "events": _safe_json_loads(row[11], []),
            }
            for row in rows
        ]

    async def get_trace_logs(self, trace_id: str) -> list[dict]:
        """Return logs matching a trace_id."""
        cursor = await self.db.execute(
            """SELECT timestamp_unix_nano, trace_id, span_id, severity_number,
                      severity_text, body, attributes, resource_attributes, service_name
               FROM logs WHERE trace_id = ?
               ORDER BY timestamp_unix_nano""",
            (trace_id,),
        )
        rows = await cursor.fetchall()
        return [self._log_row_to_dict(row) for row in rows]

    async def get_logs(
        self,
        service: str | None = None,
        severity: str | None = None,
        trace_id: str | None = None,
        span_id: str | None = None,
        since_ns: int | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Return recent logs with optional filters."""
        conditions: list[str] = []
        params: list = []
        if service:
            conditions.append("service_name = ?")
            params.append(service)
        if severity:
            conditions.append("severity_text = ?")
            params.append(severity)
        if trace_id:
            conditions.append("trace_id = ?")
            params.append(trace_id)
        if span_id:
            conditions.append("span_id = ?")
            params.append(span_id)
        if since_ns is not None:
            conditions.append("timestamp_unix_nano >= ?")
            params.append(since_ns)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT timestamp_unix_nano, trace_id, span_id, severity_number,
                   severity_text, body, attributes, resource_attributes, service_name
            FROM logs {where}
            ORDER BY timestamp_unix_nano DESC
            LIMIT ?
        """  # noqa: S608
        params.append(limit)
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [self._log_row_to_dict(row) for row in rows]

    async def get_metric_names(self, service: str | None = None) -> list[dict]:
        """Return known metric names with latest values."""
        conditions: list[str] = []
        params: list = []
        if service:
            conditions.append("service_name = ?")
            params.append(service)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        query = f"""
            SELECT name, description, unit, type, value, service_name,
                   MAX(timestamp_unix_nano)
            FROM metrics {where}
            GROUP BY name, service_name
            ORDER BY name
        """  # noqa: S608
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [
            {
                "name": row[0],
                "description": row[1],
                "unit": row[2],
                "type": row[3],
                "latest_value": row[4],
                "service_name": row[5],
            }
            for row in rows
        ]

    async def get_metric_series(
        self,
        name: str,
        service: str | None = None,
        since_ns: int | None = None,
        step_ns: int | None = None,
    ) -> list[dict]:
        """Return time series data points for a metric."""
        conditions = ["name = ?"]
        params: list = [name]
        if service:
            conditions.append("service_name = ?")
            params.append(service)
        if since_ns is not None:
            conditions.append("timestamp_unix_nano >= ?")
            params.append(since_ns)

        where = f"WHERE {' AND '.join(conditions)}"
        query = f"""
            SELECT timestamp_unix_nano, value
            FROM metrics {where}
            ORDER BY timestamp_unix_nano
        """  # noqa: S608
        cursor = await self.db.execute(query, params)
        rows = await cursor.fetchall()
        return [{"timestamp_unix_nano": row[0], "value": row[1]} for row in rows]

    async def delete_all(self) -> None:
        """Delete all stored telemetry data."""
        for table in ("spans", "logs", "metrics"):
            await self.db.execute(f"DELETE FROM {table}")  # noqa: S608
        await self.db.commit()

    async def prune(self, retain_minutes: int | None = None) -> int:
        """Delete records older than retain_minutes. Returns count deleted."""
        minutes = retain_minutes or int(
            os.environ.get("COLLECTOR_RETAIN_MINUTES", str(DEFAULT_RETAIN_MINUTES))
        )
        cutoff_ns = (int(time.time()) - minutes * 60) * 1_000_000_000
        total = 0
        for table, ts_col in [
            ("spans", "start_time_unix_nano"),
            ("logs", "timestamp_unix_nano"),
            ("metrics", "timestamp_unix_nano"),
        ]:
            cursor = await self.db.execute(
                f"DELETE FROM {table} WHERE {ts_col} < ?", (cutoff_ns,)  # noqa: S608
            )
            total += cursor.rowcount
        await self.db.commit()
        return total

    @staticmethod
    def _log_row_to_dict(row) -> dict:
        return {
            "timestamp_unix_nano": row[0],
            "trace_id": row[1],
            "span_id": row[2],
            "severity_number": row[3],
            "severity_text": row[4],
            "body": row[5],
            "attributes": _safe_json_loads(row[6], {}),
            "resource_attributes": _safe_json_loads(row[7], {}),
            "service_name": row[8],
        }
