from app.models.story import Story
from app.models.setting import Setting
from app.models.preference import UserPreference

def test_story_model():
    story = Story(
        hacker_news_id="12345",
        title="Test Story",
        url="https://example.com",
        score=100,
        author="testuser"
    )
    assert story.hacker_news_id == "12345"
    assert story.title == "Test Story"
    assert story.url == "https://example.com"
    assert story.score == 100
    assert story.author == "testuser"

def test_setting_model():
    setting = Setting(
        cron_schedule="0 9 * * *",
        min_score=100
    )
    assert setting.cron_schedule == "0 9 * * *"
    assert setting.min_score == 100

def test_preference_model():
    preference = UserPreference(
        highlight_keywords="ai,ml,dl",
        blocklist_keywords="politics,religion"
    )
    assert preference.highlight_keywords == "ai,ml,dl"
    assert preference.blocklist_keywords == "politics,religion"