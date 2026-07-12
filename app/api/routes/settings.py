"""API routes for managing application settings and triggering background tasks."""

import json
import os
from typing import List

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.setting import Setting
from app.schemas.setting import SettingResponse, SettingUpdate
from app.services.ai_service import AIService
from app.services.provider_registry import get_available_providers, get_provider
from app.shared.languages import get_languages
from app.tasks.schedule_manager import get_schedule_manager

router = APIRouter()


@router.get("/", response_model=SettingResponse)
async def get_settings(db: AsyncSession = Depends(get_db)):
    """Get application settings.

    API keys are NEVER returned to the frontend.
    Only provider availability info is sent.
    """
    result = await db.execute(select(Setting).limit(1))
    setting = result.scalar_one_or_none()
    if not setting:
        setting = Setting()
        db.add(setting)
        await db.commit()
        await db.refresh(setting)

    # Add available providers (computed from .env, not stored in DB)
    setting_dict = {c.name: getattr(setting, c.name) for c in setting.__table__.columns}
    setting_dict["id"] = setting.id
    setting_dict["available_providers"] = get_available_providers()
    setting_dict["available_languages"] = get_languages()

    # Telegram availability (computed from .env, never stored in DB)
    setting_dict["telegram_available"] = bool(settings.TELEGRAM_BOT_TOKEN)

    return setting_dict


@router.put("/", response_model=SettingResponse)
async def update_settings(
    setting_update: SettingUpdate, db: AsyncSession = Depends(get_db)
):
    """Update application settings.

    Does NOT accept API keys - those are only configured via .env file.
    """
    result = await db.execute(select(Setting).limit(1))
    setting = result.scalar_one_or_none()

    if not setting:
        setting = Setting()
        db.add(setting)

    # Update fields (ai_provider, ai_model, ai_provider_config, schedule, etc.)
    update_data = setting_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(setting, field, value)

    # If individual time/day fields are provided, update cron_schedule
    if (
        setting_update.scheduled_hour is not None
        or setting_update.scheduled_minute is not None
        or setting_update.scheduled_days is not None
    ):
        from app.tasks.scheduler import format_days_to_cron

        hour = (
            setting_update.scheduled_hour
            if setting_update.scheduled_hour is not None
            else setting.scheduled_hour or 9
        )
        minute = (
            setting_update.scheduled_minute
            if setting_update.scheduled_minute is not None
            else setting.scheduled_minute or 0
        )
        days_str = (
            setting_update.scheduled_days
            if setting_update.scheduled_days is not None
            else setting.scheduled_days or "1,2,3,4,5"
        )

        days = [int(d.strip()) for d in days_str.split(",") if d.strip().isdigit()]
        cron_schedule = format_days_to_cron(days, hour, minute)
        setting.cron_schedule = cron_schedule

        try:
            schedule_manager = await get_schedule_manager()
            await schedule_manager.update_schedule(cron_schedule)
        except Exception as e:
            print(f"[WARN] Redis schedule sync failed (non-critical): {e}")

    await db.commit()
    await db.refresh(setting)

    # Return with available providers
    setting_dict = {c.name: getattr(setting, c.name) for c in setting.__table__.columns}
    setting_dict["id"] = setting.id
    setting_dict["available_providers"] = get_available_providers()
    setting_dict["telegram_available"] = bool(settings.TELEGRAM_BOT_TOKEN)

    return setting_dict


@router.get("/available-models")
async def get_available_models(
    provider: str = Query(..., description="Provider ID"),
    config: str = Query("", description="Provider config JSON"),
):
    """Fetch available models from a provider's API.

    Provider must have its API key configured in .env file.
    For local providers (LM Studio, Ollama), config can specify base_url.
    """
    provider_def = get_provider(provider)
    if not provider_def:
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")

    # Check if provider has API key configured (for remote providers)
    env_key = provider_def.get("env_key")
    if env_key:
        from app.core.config import settings as app_settings

        env_value = getattr(app_settings, env_key, None)
        if not env_value or not str(env_value).strip():
            raise HTTPException(
                status_code=400,
                detail=f"Provider '{provider}' has no API key configured in .env",
            )

    try:
        ai_service = AIService()
        models = await ai_service.get_available_models(provider, config)
        return {"provider": provider, "models": models}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch models: {str(e)}"
        )


@router.post("/trigger-worker")
async def trigger_worker():
    """Manually trigger the worker to fetch and process stories"""
    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_CONNECTION_URL)

        # Create Redis pool
        redis_pool = await create_pool(redis_settings)

        # Enqueue the fetch and process job (send_notification=False for manual trigger)
        job = await redis_pool.enqueue_job("fetch_and_process_stories", send_notification=False)

        await redis_pool.close()  # Close the pool

        if job:
            return {
                "message": (
                    "Veri çekimi arka planda başlatıldı. "
                    "İşlem birkaç dakika sürebilir."
                ),
                "job_id": job.job_id,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Worker job could not be enqueued"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Worker başlatılamadı: {str(e)}")


@router.post("/reprocess-untranslated")
async def reprocess_untranslated():
    """Trigger reprocessing of stories that need AI translation
    with fresh content"""
    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_CONNECTION_URL)

        # Create Redis pool
        redis_pool = await create_pool(redis_settings)

        # Enqueue the reprocess job
        job = await redis_pool.enqueue_job("reprocess_untranslated_stories")

        await redis_pool.close()  # Close the pool

        if job:
            return {
                "message": (
                    "Çevrilmemiş başlıkların yeniden işlenmesi "
                    "başlatıldı. İçerik ve yorumlar tazeleniyor..."
                ),
                "job_id": job.job_id,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Reprocess job could not be enqueued"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Reprocessing başlatılamadı: {str(e)}"
        )


@router.post("/debug-untranslated")
async def debug_untranslated():
    """Debug untranslated stories"""
    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_CONNECTION_URL)

        # Create Redis pool
        redis_pool = await create_pool(redis_settings)

        # Enqueue the debug job
        job = await redis_pool.enqueue_job("debug_untranslated_stories")

        await redis_pool.close()  # Close the pool

        if job:
            return {
                "message": "Debug işlemi başlatıldı. Loglara bakın.",
                "job_id": job.job_id,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Debug job could not be enqueued"
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Debug başlatılamadı: {str(e)}")


# Add this new endpoint
@router.post("/reprocess-all")
async def reprocess_all():
    """Trigger reprocessing of ALL stories"""
    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_CONNECTION_URL)

        # Create Redis pool
        redis_pool = await create_pool(redis_settings)

        # Enqueue the reprocess job
        job = await redis_pool.enqueue_job("reprocess_all_stories")

        await redis_pool.close()  # Close the pool

        if job:
            return {
                "message": "Tüm hikayelerin yeniden işlenmesi başlatıldı.",
                "job_id": job.job_id,
            }
        else:
            raise HTTPException(
                status_code=500, detail="Reprocess job could not be enqueued"
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Reprocessing başlatılamadı: {str(e)}"
        )


@router.get("/schedule-status")
async def get_schedule_status():
    """Get current schedule status from Redis for debugging"""
    try:
        redis_settings = RedisSettings.from_dsn(settings.REDIS_CONNECTION_URL)

        # Create Redis pool
        redis_pool = await create_pool(redis_settings)

        # Get schedule info from Redis
        schedule_config = await redis_pool.get("hn_reader:schedule:config")
        schedule_version = await redis_pool.get("hn_reader:schedule:version")

        await redis_pool.close()

        return {
            "schedule_config": schedule_config,
            "schedule_version": schedule_version,
            "message": "Schedule status retrieved from Redis",
        }

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error getting schedule status: {str(e)}"
        )
