"""Tests for card search service."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from app.schemas.card import CardSearchParams
from app.services.card.search import CardSearchService


@pytest.mark.asyncio
async def test_search_returns_paginated_result():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar.return_value = 5
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute.return_value = mock_result

    svc = CardSearchService(mock_db)
    params = CardSearchParams(q="Blue-Eyes", page=1, page_size=10)
    result = await svc.search(params)

    assert "cards" in result
    assert "total" in result
    assert "page" in result
    assert result["page"] == 1


@pytest.mark.asyncio
async def test_get_by_id_returns_none_for_missing():
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_result

    svc = CardSearchService(mock_db)
    result = await svc.get_by_id(uuid4())
    assert result is None
