"""Update DB schedule to current time + 2min for testing"""
import asyncio
from datetime import datetime
from sqlalchemy import text
from app.core.config import settings
from app.core.database import AsyncSessionLocal

async def main():
    tz_offset = 3
    now_local = datetime.now()
    target_minute = now_local.minute + 2
    target_hour = now_local.hour
    if target_minute >= 60:
        target_minute -= 60
        target_hour += 1
    
    cron = f"{target_minute} {target_hour} * * 0,1,2,3,4,5,6"
    print(f"Setting DB schedule to: {cron} (local time {target_hour}:{target_minute:02d})")
    
    async with AsyncSessionLocal() as db:
        await db.execute(text(
            "UPDATE setting SET cron_schedule = :cron WHERE id = (SELECT id FROM setting LIMIT 1)"
        ), {"cron": cron})
        await db.commit()
        print("DB updated successfully")

if __name__ == "__main__":
    asyncio.run(main())