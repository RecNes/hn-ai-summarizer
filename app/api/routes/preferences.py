"""API routes for managing user preferences."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.preference import UserPreference
from app.schemas.preference import PreferenceResponse, PreferenceUpdate

router = APIRouter()


@router.get("/", response_model=PreferenceResponse)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get user preferences"""

    result = await db.execute(select(UserPreference).limit(1))
    preference = result.scalar_one_or_none()
    if not preference:
        # Create default preferences if none exist
        preference = UserPreference()
        db.add(preference)
        await db.commit()
        await db.refresh(preference)
    return preference


@router.put("/", response_model=PreferenceResponse)
async def update_preferences(
    preference_update: PreferenceUpdate, db: AsyncSession = Depends(get_db)
):
    """Update user preferences"""
    result = await db.execute(select(UserPreference).limit(1))
    preference = result.scalar_one_or_none()

    if not preference:
        preference = UserPreference()
        db.add(preference)

    # Update fields
    for field, value in preference_update.dict(exclude_unset=True).items():
        setattr(preference, field, value)

    await db.commit()
    await db.refresh(preference)
    return preference
