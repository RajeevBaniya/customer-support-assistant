from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from src.documents.ingestionJobRepository import IngestionJobRepository


@pytest.mark.asyncio
async def test_cancel_active_updates_rows() -> None:
    session = AsyncMock()
    result = MagicMock()
    result.rowcount = 2
    session.execute = AsyncMock(return_value=result)
    session.flush = AsyncMock()
    repo = IngestionJobRepository(session)
    n = await repo.cancel_active_for_document(document_id=UUID(int=1))
    assert n == 2
    session.execute.assert_awaited_once()
