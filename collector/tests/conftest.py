"""Shared fixtures for collector tests."""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from dev_collector.storage import Storage


@pytest_asyncio.fixture
async def storage():
    """Provide an in-memory SQLite storage instance."""
    s = Storage(db_path=":memory:")
    await s.connect()
    yield s
    await s.close()


@pytest.fixture
def app(storage):
    """Provide a FastAPI app with in-memory storage."""
    from dev_collector.server import app as _app
    _app.state.storage = storage
    return _app


@pytest_asyncio.fixture
async def client(app):
    """Provide an async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


SAMPLE_TRACE_ID = "0a0b0c0d0e0f1011" + "0" * 16
SAMPLE_SPAN_ID = "1a1b1c1d1e1f1011"
SAMPLE_PARENT_SPAN_ID = "2a2b2c2d2e2f2021"
SAMPLE_SERVICE_NAME = "test-service"
SAMPLE_SPAN_NAME = "GET /api/test"
SAMPLE_START_NS = 1_700_000_000_000_000_000
SAMPLE_END_NS = 1_700_000_000_100_000_000
SAMPLE_DURATION_MS = 100.0
