"""CLI entry point for running server or worker"""

import asyncio
import sys

import uvicorn
from arq import run_worker as run_worker_main

from app.core.config import settings
from app.tasks.scheduler import run_scheduler as scheduler_main
from app.tasks.worker import WorkerSettings
from app.tasks.schedule_manager import get_schedule_manager


def run_server():
    """Run the FastAPI server"""
    host = "0.0.0.0" if settings.DEVELOPMENT else "127.0.0.1"
    uvicorn.run("app.main:app", host=host, port=8000, reload=settings.DEVELOPMENT)


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
    print("Starting scheduler...")
    asyncio.run(scheduler_main())
    print("Scheduler started.")


def test_schedule_sync():
    """Test schedule synchronization between processes"""

    async def _test():
        print("Testing schedule synchronization...")

        # Get schedule manager
        schedule_manager = await get_schedule_manager()

        # Test 1: Set a schedule
        test_cron = "0 10 * * 1,2,3"  # 10:00 on Mon, Tue, Wed
        print(f"Setting schedule to: {test_cron}")
        success = await schedule_manager.update_schedule(test_cron)

        if success:
            print("✓ Schedule updated in Redis")

            # Test 2: Get the schedule back
            config = await schedule_manager.get_schedule_config()
            if config and config.get("cron_schedule") == test_cron:
                print("✓ Schedule correctly stored in Redis")
                print(f"  Stored config: {config}")
            else:
                print("✗ Schedule not found or incorrect in Redis")

            # Test 3: Apply schedule locally
            from app.tasks.schedule_manager import _scheduler_tasks

            applied = await schedule_manager.apply_schedule_from_redis()
            if applied:
                print("✓ Schedule applied to TimedScheduler")
                print(f"  Current scheduled tasks: {len(_scheduler_tasks)}")
                for task_ref in _scheduler_tasks:
                    print(f"    - {task_ref}")
            else:
                print("✗ Failed to apply schedule locally")
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
