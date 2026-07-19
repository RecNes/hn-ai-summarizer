"""Unit tests for Pydantic schemas."""
# pylint: disable=undefined-variable
from datetime import datetime, timezone
from app.schemas.story import StoryCreate, StoryResponse
from app.schemas.setting import SettingBase, SettingUpdate, SettingResponse
from app.schemas.preference import PreferenceBase, PreferenceResponse
from app.schemas.activity_log import AiActivityLogResponse


class TestStorySchemas:
    """Test story Pydantic schemas."""

    def test_story_create_minimal(self):
        """StoryCreate with only required fields."""
        data = {
            "hacker_news_id": "12345",
            "title": "Test Story",
            "score": 100,
            "author": "testuser",
        }
        schema = StoryCreate(**data)
        assert schema.hacker_news_id == "12345"
        assert schema.title == "Test Story"
        assert schema.score == 100
        assert schema.author == "testuser"
        assert schema.url is None
        assert schema.is_highlighted is False

    def test_story_create_all_fields(self):
        """StoryCreate with all optional fields."""
        data = {
            "hacker_news_id": "67890",
            "title": "Full Story",
            "title_tr": "Tam Hikaye",
            "url": "https://example.com",
            "score": 200,
            "author": "author1",
            "content": "Some content",
            "content_tr": "Bazı içerik",
            "comments_summary": "Good comments",
            "image_url": "https://example.com/img.jpg",
            "is_highlighted": True,
            "is_dimmed": False,
            "is_blocked": False,
            "is_translated": True,
            "is_read": False,
        }
        schema = StoryCreate(**data)
        assert schema.title_tr == "Tam Hikaye"
        assert schema.is_translated is True
        assert schema.content == "Some content"

    def test_story_response_from_attributes(self):
        """StoryResponse with from_attributes enabled."""
        now = datetime.now(timezone.utc)
        data = {
            "id": 1,
            "hacker_news_id": "12345",
            "title": "Test",
            "score": 50,
            "author": "user",
            "created_at": now,
            "hn_created_at": now,
            "updated_at": None,
        }
        schema = StoryResponse(**data)
        assert schema.id == 1
        assert schema.created_at == now
        assert schema.updated_at is None


class TestSettingSchemas:
    """Test setting Pydantic schemas."""

    def test_setting_base_defaults(self):
        """SettingBase default values."""
        schema = SettingBase()
        assert schema.ai_provider is None
        assert schema.ai_model is None
        assert schema.telegram_enabled is False
        assert schema.cron_schedule is None

    def test_setting_base_with_values(self):
        """SettingBase with provided values."""
        schema = SettingBase(
            ai_provider="openai",
            cron_schedule="0 9 * * *",
            min_score=100,
            telegram_enabled=True,
        )
        assert schema.ai_provider == "openai"
        assert schema.min_score == 100
        assert schema.telegram_enabled is True

    def test_setting_update_partial(self):
        """SettingUpdate with partial fields."""
        schema = SettingUpdate(min_score=200)
        assert schema.min_score == 200
        assert schema.ai_provider is None
        assert schema.telegram_enabled is False

    def test_setting_response_additional_fields(self):
        """SettingResponse includes extra fields."""
        schema = SettingResponse(
            id=1,
            available_providers=[{"name": "openai"}],
            telegram_available=True,
        )
        assert schema.id == 1
        assert schema.available_providers == [{"name": "openai"}]
        assert schema.telegram_available is True


class TestPreferenceSchema:
    """Test PreferenceBase schema."""

    def test_preference_defaults(self):
        """PreferenceBase default language values."""
        schema = PreferenceBase()
        assert schema.ui_language == "en"
        assert schema.translation_language == "en"
        assert schema.highlight_keywords is None
        assert schema.blocklist_keywords is None

    def test_preference_with_keywords(self):
        """PreferenceBase with keywords set."""
        schema = PreferenceBase(
            highlight_keywords="ai,ml,python",
            blocklist_keywords="politics",
            ui_language="tr",
            translation_language="tr",
        )
        assert schema.highlight_keywords == "ai,ml,python"
        assert schema.blocklist_keywords == "politics"
        assert schema.ui_language == "tr"


class TestActivityLogSchema:  # pylint: disable=undefined-variable
    """Test AiActivityLogResponse schema."""

    def test_activity_log_minimal(self):
        """AiActivityLogResponse with all fields."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        schema = AiActivityLogResponse(
            id=1,
            event_type="translate",
            provider="openai",
            model="gpt-4",
            status="success",
            created_at=now,
        )
        assert schema.event_type == "translate"
        assert schema.provider == "openai"
        assert schema.model == "gpt-4"
        assert schema.status == "success"
        assert schema.error_message is None
        assert schema.duration_ms is None
        assert schema.id == 1

    def test_activity_log_with_error(self):
        """AiActivityLogResponse with error details."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        schema = AiActivityLogResponse(
            id=2,
            event_type="summarize",
            provider="ollama",
            model="llama2",
            status="failed",
            error_message="Timeout",
            duration_ms=5000.0,
            story_id=42,
            story_title="Test",
            created_at=now,
        )
        assert schema.status == "failed"
        assert schema.error_message == "Timeout"
        assert schema.duration_ms == 5000.0
        assert schema.story_id == 42
