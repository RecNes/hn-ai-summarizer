"""Merkezi Story CRUD servisi.

Tüm Story tablosu okuma/yazma işlemleri bu servis üzerinden yapılır.
commit/rollback işlemleri sadece bu servis içinde gerçekleşir.
Worker ve route'lar doğrudan session.commit() çağırmaz.
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.story import Story

logger = logging.getLogger(__name__)


class StoryServiceError(Exception):
    """Base exception for StoryService errors."""


class StoryNotFoundError(StoryServiceError):
    """Raised when a story is not found."""


class StoryService:
    """Merkezi Story CRUD servisi."""

    # ── Yardımcı ─────────────────────────────────────

    @staticmethod
    async def _get_by_field(
        session: AsyncSession, field: str, value: Any
    ) -> Optional[Story]:
        """Generic: sorgula ve tek Story döndür."""
        result = await session.execute(
            select(Story).where(getattr(Story, field) == value)
        )
        return result.scalar_one_or_none()

    # ── Sorgular ─────────────────────────────────────

    @staticmethod
    async def get_by_id(session: AsyncSession, story_id: int) -> Optional[Story]:
        """ID'ye göre story getir."""
        return await StoryService._get_by_field(session, "id", story_id)

    @staticmethod
    async def get_by_hn_id(
        session: AsyncSession, hn_id: str
    ) -> Optional[Story]:
        """Hacker News ID'ye göre story getir."""
        return await StoryService._get_by_field(session, "hacker_news_id", hn_id)

    @staticmethod
    async def get_untranslated(session: AsyncSession) -> List[Story]:
        """Çevirisi tamamlanmamış story'leri getir."""
        result = await session.execute(
            select(Story)
            .where((Story.is_translated.is_(None)) | (Story.is_translated == False))
            .order_by(Story.created_at.desc())
        )
        return list(result.scalars().all())

    @staticmethod
    async def get_all(
        session: AsyncSession, skip: int = 0, limit: int = 20
    ) -> List[Story]:
        """Tüm story'leri sayfalanmış şekilde getir."""
        result = await session.execute(
            select(Story).order_by(Story.created_at.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    # ── Yazma İşlemleri ──────────────────────────────

    @staticmethod
    async def create(
        session: AsyncSession, story_data: Dict[str, Any]
    ) -> Story:
        """Yeni bir Story kaydı oluştur.

        Args:
            session: AsyncSession
            story_data: Sözlük, Story alanlarıyla eşleşen key/value içerir.
                Zorunlu: hacker_news_id, title
                Opsiyonel: title_tr, url, score, author, content, content_tr,
                          comments_summary, hn_created_at, is_blocked, is_translated

        Returns:
            Oluşturulan Story nesnesi

        Raises:
            StoryServiceError: Kayıt sırasında hata oluşursa
        """
        try:
            title_tr = story_data.get("title_tr")
            content_tr = story_data.get("content_tr")
            comments_summary = story_data.get("comments_summary")

            story = Story(
                hacker_news_id=story_data.get("hacker_news_id"),
                title=story_data.get("title", ""),
                title_tr=title_tr,
                url=story_data.get("url"),
                score=story_data.get("score"),
                author=story_data.get("author"),
                content=story_data.get("content"),
                content_tr=content_tr,
                comments_summary=comments_summary,
                hn_created_at=story_data.get("hn_created_at"),
                is_blocked=story_data.get("is_blocked", False),
            )
            # is_translated belirtilmemişse otomatik hesapla
            is_translated = story_data.get("is_translated")
            if is_translated is None:
                story.is_translated = bool(
                    title_tr
                    and content_tr
                    and comments_summary
                    and not (title_tr or "").startswith("[TR]")
                )
            else:
                story.is_translated = is_translated

            session.add(story)
            await session.commit()
            await session.refresh(story)
            logger.info(f"Story created: HN={story.hacker_news_id}, id={story.id}")
            return story
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to create story: {e}")
            raise StoryServiceError(f"Story oluşturulamadı: {e}") from e

    @staticmethod
    async def update_translations(
        session: AsyncSession,
        story: Story,
        title_tr: Optional[str] = None,
        content_tr: Optional[str] = None,
        comments_summary: Optional[str] = None,
        is_translated: Optional[bool] = None,
    ) -> Story:
        """Bir story'nin AI çeviri/özet alanlarını güncelle.

        Args:
            session: AsyncSession
            story: Güncellenecek Story nesnesi
            title_tr: Türkçe başlık (None = değiştirme)
            content_tr: Türkçe özet (None = değiştirme)
            comments_summary: Yorum özeti (None = değiştirme)
            is_translated: Çeviri tamam mı? (None = otomatik hesapla)

        Returns:
            Güncellenmiş Story nesnesi
        """
        try:
            if title_tr is not None:
                story.title_tr = title_tr
            if content_tr is not None:
                story.content_tr = content_tr
            if comments_summary is not None:
                story.comments_summary = comments_summary

            if is_translated is not None:
                story.is_translated = is_translated
            else:
                # Otomatik hesapla: tüm çeviri alanları dolu mu?
                story.is_translated = bool(
                    story.title_tr
                    and story.content_tr
                    and story.comments_summary
                    and not (story.title_tr or "").startswith("[TR]")
                )

            await session.commit()
            await session.refresh(story)
            logger.debug(f"Story {story.id} translations updated")
            return story
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update story translations: {e}")
            raise StoryServiceError(
                f"Story çevirileri güncellenemedi: {e}"
            ) from e

    @staticmethod
    async def update_from_fetch(
        session: AsyncSession,
        story: Story,
        fresh_data: Dict[str, Any],
    ) -> Story:
        """HN'den tazelenen veriyle story alanlarını güncelle.

        title, url, score, author, content alanlarını günceller.

        Args:
            session: AsyncSession
            story: Güncellenecek Story
            fresh_data: Fetcher'dan gelen taze veri sözlüğü

        Returns:
            Güncellenmiş Story
        """
        try:
            if fresh_data.get("title"):
                story.title = fresh_data["title"]
            if fresh_data.get("url"):
                story.url = fresh_data["url"]
            if fresh_data.get("score") is not None:
                story.score = fresh_data["score"]
            if fresh_data.get("author"):
                story.author = fresh_data["author"]
            if fresh_data.get("content") is not None:
                story.content = fresh_data["content"]

            await session.commit()
            await session.refresh(story)
            logger.debug(f"Story {story.id} data refreshed from HN")
            return story
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to update story from fetch: {e}")
            raise StoryServiceError(
                f"Story HN verisi güncellenemedi: {e}"
            ) from e

    @staticmethod
    async def toggle_read(
        session: AsyncSession, story_id: int
    ) -> Story:
        """Bir story'nin is_read değerini tersine çevir.

        Args:
            session: AsyncSession
            story_id: Story ID

        Returns:
            Güncellenmiş Story

        Raises:
            StoryNotFoundError: Story bulunamazsa
        """
        story = await StoryService.get_by_id(session, story_id)
        if not story:
            raise StoryNotFoundError(f"Story #{story_id} bulunamadı")

        try:
            story.is_read = not story.is_read
            await session.commit()
            await session.refresh(story)
            logger.info(f"Story {story_id} read status toggled to {story.is_read}")
            return story
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to toggle story read status: {e}")
            raise StoryServiceError(
                f"Story okuma durumu değiştirilemedi: {e}"
            ) from e

    @staticmethod
    async def block_story(
        session: AsyncSession, story_id: int
    ) -> Story:
        """Bir story'yi negatif feedback ile blokele.

        Args:
            session: AsyncSession
            story_id: Story ID

        Returns:
            Güncellenmiş Story

        Raises:
            StoryNotFoundError: Story bulunamazsa
        """
        story = await StoryService.get_by_id(session, story_id)
        if not story:
            raise StoryNotFoundError(f"Story #{story_id} bulunamadı")

        try:
            story.is_blocked = True
            await session.commit()
            await session.refresh(story)
            logger.info(f"Story {story_id} blocked (negative feedback)")
            return story
        except Exception as e:
            await session.rollback()
            logger.error(f"Failed to block story: {e}")
            raise StoryServiceError(
                f"Story bloklanamadı: {e}"
            ) from e