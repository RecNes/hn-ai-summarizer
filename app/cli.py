"""CLI entry point for running server or worker"""

import asyncio
import sys

import uvicorn
from arq import run_worker as run_worker_main

from app.core.config import settings
from app.tasks.schedule_manager import update_schedule
from app.tasks.scheduler import run_scheduler as scheduler_main
from app.tasks.worker import WorkerSettings


def run_server():
    """Run the FastAPI server"""
    host = "0.0.0.0" if settings.DEVELOPMENT else "127.0.0.1"
    uvicorn.run(
        "app.main:app",
        host=host,
        port=8000,
        reload=settings.DEVELOPMENT,
    )


def run_all():
    """Run all services (server, worker, and scheduler)"""
    import subprocess
    import sys

    processes = []

    try:
        # Start worker
        print("Starting worker...")
        worker_proc = subprocess.Popen(["hn-ai-summerizer", "worker"])
        processes.append(worker_proc)

        # Start scheduler
        print("Starting scheduler...")
        scheduler_proc = subprocess.Popen(["hn-ai-summerizer", "scheduler"])
        processes.append(scheduler_proc)

        # Start server (this will block)
        print("Starting server...")
        server_proc = subprocess.Popen(["hn-ai-summerizer", "server"])
        processes.append(server_proc)

        # Wait for server to finish (Ctrl+C)
        server_proc.wait()

    except KeyboardInterrupt:
        print("\nShutting down all services...")
        for proc in processes:
            proc.terminate()
        for proc in processes:
            proc.wait()
        print("All services stopped.")
    except Exception as e:
        print(f"Error: {e}")
        for proc in processes:
            proc.terminate()
        sys.exit(1)


def run_worker():
    """Run the Arq worker"""
    run_worker_main(WorkerSettings)  # type: ignore


def run_scheduler():
    """Run the scheduler"""
    from app.core.logging_config import setup_logging
    setup_logging()
    print("Starting scheduler...")
    asyncio.run(scheduler_main())


def test_schedule_sync():
    """Test schedule synchronization between processes"""

    async def _test():
        print("Testing schedule synchronization...")

        test_cron = "0 10 * * 1,2,3"
        print(f"Setting schedule to: {test_cron}")
        success = await update_schedule(test_cron)

        if success:
            print("✓ Schedule updated in Redis")

            import json
            from app.tasks.schedule_manager import _get_redis_pool
            pool = await _get_redis_pool()
            raw = await pool.get("hn_reader:schedule:config")
            config = json.loads(raw) if raw else None
            await pool.aclose()

            if config and config.get("cron_schedule") == test_cron:
                print("✓ Schedule correctly stored in Redis")
                print(f"  Stored config: {config}")
            else:
                print("✗ Schedule not found or incorrect in Redis")
        else:
            print("✗ Failed to update schedule in Redis")

    asyncio.run(_test())


def main():
    """Main CLI entry point"""
    if len(sys.argv) < 2:
        print("Usage: hn-ai-summerizer [server|worker|scheduler|all|test-schedule]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "server":
        run_server()
    elif command == "worker":
        run_worker()
    elif command == "scheduler":
        run_scheduler()
    elif command == "all":
        run_all()
    elif command == "test-schedule":
        test_schedule_sync()
    else:
        print(f"Unknown command: {command}")
        print("Usage: hn-ai-summerizer [server|worker|scheduler|all|test-schedule]")
        sys.exit(1)


if __name__ == "__main__":
    main()
