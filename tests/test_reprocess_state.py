"""Unit tests for reprocess state service."""
from unittest.mock import AsyncMock, patch


from app.services.reprocess_state import (
    _unhash,
    get_reprocess_state,
    set_reprocess_state,
    reset_reprocess_state,
)


class TestUnhash:
    """Test _unhash helper function."""

    def test_running_true(self):
        result = _unhash({"running": "1"})
        assert result["running"] is True

    def test_running_false(self):
        result = _unhash({"running": "0"})
        assert result["running"] is False

    def test_numeric_fields(self):
        result = _unhash({"current": "5", "total": "10", "percentage": "50"})
        assert result["current"] == 5
        assert result["total"] == 10
        assert result["percentage"] == 50

    def test_story_id_int(self):
        result = _unhash({"story_id": "42"})
        assert result["story_id"] == 42

    def test_story_id_none(self):
        result = _unhash({"story_id": "None"})
        assert result["story_id"] is None

    def test_cancelled_true(self):
        result = _unhash({"cancelled": "1"})
        assert result["cancelled"] is True

    def test_cancelled_false(self):
        result = _unhash({"cancelled": "0"})
        assert result["cancelled"] is False

    def test_empty_data(self):
        result = _unhash({})
        assert result["running"] is False
        assert result["current"] == 0
        assert result["total"] == 0
        assert result["percentage"] == 0
        assert result["story_id"] == 0  # defaults to 0 for missing key
        assert result["cancelled"] is False


class TestGetReprocessState:
    """Test get_reprocess_state function."""

    @patch("app.services.reprocess_state.aioredis.from_url")
    async def test_returns_data(self, mock_from_url):
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "running": "1",
            "current": "10",
            "total": "50",
            "percentage": "20",
            "story_id": "123",
            "cancelled": "0",
        }
        mock_from_url.return_value = mock_redis

        result = await get_reprocess_state()

        assert result["running"] is True
        assert result["current"] == 10
        assert result["total"] == 50
        assert result["percentage"] == 20
        assert result["story_id"] == 123

    @patch("app.services.reprocess_state.aioredis.from_url")
    async def test_no_data_returns_defaults(self, mock_from_url):
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}
        mock_from_url.return_value = mock_redis

        result = await get_reprocess_state()

        assert result == {
            "running": False,
            "current": 0,
            "total": 0,
            "percentage": 0,
            "story_id": None,
            "cancelled": False,
        }

    @patch("app.services.reprocess_state.aioredis.from_url")
    async def test_redis_error_returns_defaults(self, mock_from_url):
        mock_from_url.side_effect = Exception("Connection refused")

        result = await get_reprocess_state()

        assert result["running"] is False
        assert result["current"] == 0


class TestSetReprocessState:
    """Test set_reprocess_state function."""

    @patch("app.services.reprocess_state.aioredis.from_url")
    async def test_sets_running_true(self, mock_from_url):
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}
        mock_from_url.return_value = mock_redis

        await set_reprocess_state(running=True)

        call_kwargs = mock_redis.hset.call_args[1]["mapping"]
        assert call_kwargs["running"] == "1"

    @patch("app.services.reprocess_state.aioredis.from_url")
    async def test_sets_running_false(self, mock_from_url):
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {}
        mock_from_url.return_value = mock_redis

        await set_reprocess_state(running=False)

        call_kwargs = mock_redis.hset.call_args[1]["mapping"]
        assert call_kwargs["running"] == "0"

    @patch("app.services.reprocess_state.aioredis.from_url")
    async def test_merges_with_existing(self, mock_from_url):
        mock_redis = AsyncMock()
        mock_redis.hgetall.return_value = {
            "running": "1",
            "current": "5",
            "total": "10",
            "percentage": "50",
            "story_id": "42",
            "cancelled": "0",
        }
        mock_from_url.return_value = mock_redis

        await set_reprocess_state(current=8)

        call_kwargs = mock_redis.hset.call_args[1]["mapping"]
        assert call_kwargs["current"] == "8"
        assert call_kwargs["total"] == "10"
        assert call_kwargs["running"] == "1"

    @patch("app.services.reprocess_state.aioredis.from_url")
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