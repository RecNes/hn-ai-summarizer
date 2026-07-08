"""Script to run the scheduler for periodic tasks."""

import asyncio
import os
import sys

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.tasks.scheduler import run_scheduler


async def main():
    """Run the scheduler"""
    print("Starting scheduler...")
    await run_scheduler()


if __name__ == "__main__":
    asyncio.run(main())
