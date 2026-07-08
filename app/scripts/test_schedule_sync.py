"""Test script to verify Redis-based schedule synchronization between processes."""

import asyncio
import sys

from arq import create_pool
from arq.connections import RedisSettings

from app.core.config import settings
from app.tasks.schedule_manager import ScheduleManager


async def test_redis_connection():
    """Test Redis connection."""
    print("Testing Redis connection...")

    try:
        redis_url = settings.REDIS_URL or "redis://localhost:6379/0"
        redis_settings = RedisSettings.from_dsn(redis_url)
        redis_pool = await create_pool(redis_settings)

        # Test basic operations
        await redis_pool.set("test_key", "test_value")
        value = await redis_pool.get("test_key")
        await redis_pool.delete("test_key")

        await redis_pool.close()

        if value == b"test_value":
            print("✓ Redis connection successful")
            return True
        else:
            print("✗ Redis connection failed - unexpected value")
            return False

    except Exception as e:
        print(f"✗ Redis connection failed: {e}")
        return False


async def test_schedule_manager():
    """Test ScheduleManager functionality."""
    print("\nTesting ScheduleManager...")

    try:
        # Initialize schedule manager
        manager = ScheduleManager()
        await manager.initialize()

        # Test 1: Set initial schedule
        test_cron = "0 10 * * 1,2,3"  # 10:00 on Mon, Tue, Wed
        print(f"Setting schedule to: {test_cron}")

        success = await manager.update_schedule(test_cron)
        if not success:
            print("✗ Failed to update schedule")
            return False

        print("✓ Schedule updated in Redis")

        # Test 2: Get schedule config
        config = await manager.get_schedule_config()
        if not config or config.get("cron_schedule") != test_cron:
            print(f"✗ Schedule config incorrect: {config}")
            return False

        print(f"✓ Schedule config correct: {config}")

        # Test 3: Get schedule version
        version = await manager.get_schedule_version()
        print(f"✓ Schedule version: {version}")

        # Test 4: Apply schedule locally
        applied = await manager.apply_schedule_from_redis()
        if not applied:
            print("✗ Failed to apply schedule locally")
            return False

        print("✓ Schedule applied to local aioschedule")

        # Test 5: Test lock mechanism
        lock_acquired = await manager.acquire_lock()
        if not lock_acquired:
            print("✗ Failed to acquire lock")
            return False

        print("✓ Lock acquired successfully")

        await manager.release_lock()
        print("✓ Lock released successfully")

        return True

    except Exception as e:
        print(f"✗ ScheduleManager test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_concurrent_updates():
    """Test concurrent schedule updates from multiple processes."""
    print("\nTesting concurrent schedule updates...")

    try:
        # Create two schedule managers (simulating different processes)
        manager1 = ScheduleManager()
        manager2 = ScheduleManager()

        await manager1.initialize()
        await manager2.initialize()

        # Test 1: Manager 1 sets schedule
        cron1 = "0 9 * * 1,3,5"  # 9:00 on Mon, Wed, Fri
        print(f"Manager 1 setting schedule: {cron1}")
        success1 = await manager1.update_schedule(cron1)

        if not success1:
            print("✗ Manager 1 failed to update schedule")
            return False

        # Test 2: Manager 2 reads the same schedule
        config2 = await manager2.get_schedule_config()
        if not config2 or config2.get("cron_schedule") != cron1:
            print(f"✗ Manager 2 got different schedule: {config2}")
            return False

        print("✓ Manager 2 sees same schedule as Manager 1")

        # Test 3: Manager 2 updates schedule
        cron2 = "30 14 * * 2,4"  # 14:30 on Tue, Thu
        print(f"Manager 2 setting schedule: {cron2}")
        success2 = await manager2.update_schedule(cron2)

        if not success2:
            print("✗ Manager 2 failed to update schedule")
            return False

        # Test 4: Manager 1 reads the updated schedule
        config1 = await manager1.get_schedule_config()
        if not config1 or config1.get("cron_schedule") != cron2:
            print(f"✗ Manager 1 got different schedule: {config1}")
            return False

        print("✓ Manager 1 sees updated schedule from Manager 2")

        return True

    except Exception as e:
        print(f"✗ Concurrent updates test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def test_schedule_parsing():
    """Test cron schedule parsing functions."""
    print("\nTesting schedule parsing...")

    try:
        from app.tasks.scheduler import parse_cron_to_time, parse_cron_to_days

        # Test time parsing
        test_cases = [
            ("0 9 * * *", "09:00"),
            ("30 14 * * *", "14:30"),
            ("15 8 * * *", "08:15"),
            ("invalid", "09:00"),  # Should default
        ]

        for cron, expected_time in test_cases:
            result = parse_cron_to_time(cron)
            if result != expected_time:
                print(
                    f"✗ Time parsing failed for {cron}: got {result}, expected {expected_time}"
                )
                return False

        print("✓ Time parsing works correctly")

        # Test days parsing
        day_cases = [
            ("0 9 * * 1,3,5", [1, 3, 5]),
            ("0 9 * * 1-3", [1, 2, 3]),
            ("0 9 * * 5", [5]),
            ("0 9 * * *", []),
            ("invalid", [1, 2, 3, 4, 5]),  # Should default
        ]

        for cron, expected_days in day_cases:
            result = parse_cron_to_days(cron)
            if result != expected_days:
                print(
                    f"✗ Days parsing failed for {cron}: got {result}, expected {expected_days}"
                )
                return False

        print("✓ Days parsing works correctly")

        return True

    except Exception as e:
        print(f"✗ Schedule parsing test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("=== Redis-based Schedule Synchronization Test ===\n")

    tests = [
        test_redis_connection,
        test_schedule_manager,
        test_concurrent_updates,
        test_schedule_parsing,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            result = await test()
            if result:
                passed += 1
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            print()

    print(f"=== Test Results: {passed}/{total} tests passed ===")

    if passed == total:
        print("🎉 All tests passed! Redis-based scheduling is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
