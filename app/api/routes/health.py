"""Health check endpoint for the HN-AI-Summerizer API."""

from fastapi import APIRouter, Depends
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db

router = APIRouter()


@router.get("/")
async def health_check(db: AsyncSession = Depends(get_db)):
    """Comprehensive health check"""
    db_status = "unknown"

    try:
        # Check database connection
        await db.execute(select(1))
        db_status = "healthy"
    except SQLAlchemyError as e:
        db_status = f"unhealthy: Database error - {str(e)}"
    except Exception as e:  # pylint: disable=broad-except
        db_status = f"unhealthy: Unexpected error - {str(e)}"

    return {
        "status": "healthy" if db_status == "healthy" else "unhealthy",
        "database": db_status,
        "service": "HN-AI-Summerizer API",
    }
