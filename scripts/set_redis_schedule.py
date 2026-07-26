"""Set Redis schedule to trigger 2 minutes from now"""
import asyncio
import json
from datetime import datetime
from arq import create_pool
from arq.connections import RedisSettings
from app.core.config import settings

async def main():
    now_local = datetime.now()
    target_minute = now_local.minute + 2
    target_hour = now_local.hour
    if target_minute >= 60:
        target_minute -= 60
        target_hour += 1
    
    cron = f"{target_minute} {target_hour} * * 0,1,2,3,4,5,6"
    print(f"Setting Redis schedule to: {cron}")
    
    pool = await create_pool(RedisSettings.from_dsn(
        settings.REDIS_CONNECTION_URL or "redis://localhost:6379/0"
    ))
    
    await pool.set("hn_reader:schedule:config", json.dumps({"cron_schedule": cron}))
    
    v = await pool.get("hn_reader:schedule:version")
    nv = str(int(v) + 1 if v else 1)
    await pool.set("hn_reader:schedule:version", nv)
    print(f"Done (version={nv})")
    
    await pool.aclose()

if __name__ == "__main__":
    asyncio.run(main())