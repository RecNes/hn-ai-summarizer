"""Unit tests for reprocess state service."""
from unittest.mock import AsyncMock, patch

import time

from app.services.reprocess_state import (
    get_reprocess_state,
    set_reprocess_state,
    reset_reprocess_state,
)


DEFAULT_EMPTY_STATE = {
    "running": False,
    "current": 0,
    "total": 0,
    "percentage": 0,
    "story_id": None,
    "cancelled": False,
    "last_heartbeat": None,
}

DEFAULT_HASHED_STATE = {
    "running": False,
    "current": 0,
    "total": 0,
    "percentage": 0,
    "story_id": None,
    "cancelled": False,
    "last_heartbeat": None,
}


class TestGetReprocessState:
    """Test get_reprocess_state function."""

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_returns_data(self, mock_from_url):
        import json

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({
            "running": True,
            "current": 10,
            "total": 50,
            "percentage": 20,
            "story_id": 123,
            "cancelled": False,
            "last_heartbeat": time.time(),
        })
        mock_from_url.return_value = mock_redis

        result = await get_reprocess_state()

        assert result["running"] is True
        assert result["current"] == 10
        assert result["total"] == 50
        assert result["percentage"] == 20
        assert result["story_id"] == 123

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_no_data_returns_defaults(self, mock_from_url):
        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_from_url.return_value = mock_redis

        result = await get_reprocess_state()

        assert result == DEFAULT_EMPTY_STATE

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_redis_error_returns_defaults(self, mock_from_url):
        mock_from_url.side_effect = Exception("Connection refused")

        result = await get_reprocess_state()

        assert result["running"] is False
        assert result["current"] == 0

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_stuck_state_with_old_heartbeat_auto_resets(self, mock_from_url):
        import json

        mock_redis = AsyncMock()
        # 2 dakika önce heartbeat – timeout (60s) aşıldı
        old_hb = time.time() - 120
        mock_redis.get.return_value = json.dumps({
            "running": True,
            "current": 5,
            "total": 50,
            "percentage": 10,
            "story_id": 42,
            "cancelled": False,
            "last_heartbeat": old_hb,
        })
        mock_from_url.return_value = mock_redis

        result = await get_reprocess_state()

        # Stuck state auto-reset edilmiş olmalı
        assert result["running"] is False
        assert result["current"] == 0
        assert result["last_heartbeat"] is None

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_stuck_state_no_heartbeat_auto_resets(self, mock_from_url):
        import json

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({
            "running": True,
            "current": 5,
            "total": 50,
            "percentage": 10,
            "story_id": 42,
            "cancelled": False,
            "last_heartbeat": None,
        })
        mock_from_url.return_value = mock_redis

        result = await get_reprocess_state()

        # heartbeat yok → stuck kabul et ve resetle
        assert result["running"] is False
        assert result["current"] == 0


class TestSetReprocessState:
    """Test set_reprocess_state function."""

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_sets_running_true(self, mock_from_url):
        import json

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None  # no previous state
        mock_from_url.return_value = mock_redis

        await set_reprocess_state(running=True)

        call_args = mock_redis.set.call_args[0][1]
        payload = json.loads(call_args)
        assert payload["running"] is True

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_sets_running_false(self, mock_from_url):
        import json

        mock_redis = AsyncMock()
        mock_redis.get.return_value = None
        mock_from_url.return_value = mock_redis

        await set_reprocess_state(running=False)

        call_args = mock_redis.set.call_args[0][1]
        payload = json.loads(call_args)
        assert payload["running"] is False

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_merges_with_existing(self, mock_from_url):
        import json

        mock_redis = AsyncMock()
        mock_redis.get.return_value = json.dumps({
            "running": True,
            "current": 5,
            "total": 10,
            "percentage": 50,
            "story_id": 42,
            "cancelled": False,
            "last_heartbeat": time.time(),
        })
        mock_from_url.return_value = mock_redis

        await set_reprocess_state(current=8)

        call_args = mock_redis.set.call_args[0][1]
        payload = json.loads(call_args)
        assert payload["current"] == 8
        assert payload["total"] == 10
        assert payload["running"] is True
        # last_heartbeat güncellenmiş olmalı
        assert payload["last_heartbeat"] is not None

    @patch("app.services.reprocess_state.Redis.from_url")
    async def test_error_does_not_raise(self, mock_from_url):
        mock_from_url.side_effect = Exception("Redis error")

        await set_reprocess_state(running=True)


class TestResetReprocessState:
    """Test reset_reprocess_state function."""

    @patch("app.services.reprocess_state.set_reprocess_state")
    async def test_resets_all_fields(self, mock_set):
        await reset_reprocess_state()

        mock_set.assert_called_once_with(
            running=False,
            current=0,
            total=0,
            percentage=0,
            story_id=None,
            cancelled=False,
        )