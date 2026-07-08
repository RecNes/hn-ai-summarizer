# Redis-Based Schedule Synchronization

## Overview

This document describes the Redis-based schedule synchronization solution implemented to resolve scheduling inconsistencies between the app and scheduler processes.

## Problem

Previously, the application had two separate Python processes (app and scheduler) each maintaining their own independent `aioschedule.jobs` list in memory. When schedule settings were updated through the app's API, only the app process was affected, while the scheduler process continued with the old schedule configuration.

## Solution

The solution implements a Redis-based shared state system where:

1. **Schedule Configuration**: Schedule settings are stored in Redis as JSON
2. **Version Tracking**: A version number tracks changes for cache invalidation
3. **Process Synchronization**: Both processes read from and write to the same Redis store
4. **Real-time Updates**: Processes monitor Redis for changes and update their local schedules

## Architecture

```
┌─────────────────┐    Redis Store     ┌─────────────────┐
│   App Process   │  ┌─────────────┐   │ Scheduler Process │
│                 │  │ Schedule:   │   │                 │
│  API Settings   │◄►│ {"cron":    │◄►│  Schedule       │
│  Update         │  │  "0 9 * * *"}   │  Monitor        │
│                 │  │ Version: 1  │   │                 │
└─────────────────┘  └─────────────┘   └─────────────────┘
```

## Components

### 1. ScheduleManager (`app/tasks/schedule_manager.py`)

The core component that manages schedule state in Redis:

- **`update_schedule(cron_schedule)`**: Updates schedule in Redis and applies locally
- **`apply_schedule_from_redis()`**: Applies Redis schedule to local aioschedule
- **`monitor_schedule_changes()`**: Background task monitoring for changes
- **Lock mechanism**: Prevents race conditions during updates

### 2. Redis Keys

- **`hn_reader:schedule:config`**: JSON configuration with cron schedule
- **`hn_reader:schedule:version`**: Version number for cache invalidation
- **`hn_reader:schedule:lock`**: Lock key for atomic updates

### 3. Schedule Format

```json
{
  "cron_schedule": "0 9 * * 1,2,3",
  "updated_at": 1234567890.123
}
```

## Usage

### CLI Commands

```bash
# Start all services (server, worker, scheduler)
hn-ai-summerizer all

# Test schedule synchronization
hn-ai-summerizer test-schedule

# Run individual services
hn-ai-summerizer server
hn-ai-summerizer worker
hn-ai-summerizer scheduler
```

### API Endpoints

```http
GET /api/settings/schedule-status
# Returns current schedule status from Redis

POST /api/settings/
# Updates schedule and synchronizes across processes
```

### Testing

Run the comprehensive test suite:

```bash
python app/scripts/test_schedule_sync.py
```

## Implementation Details

### Schedule Updates

1. **Lock Acquisition**: Process acquires Redis lock
2. **Update Redis**: Store new schedule configuration
3. **Increment Version**: Update version for cache invalidation
4. **Release Lock**: Allow other processes to proceed
5. **Apply Locally**: Update local aioschedule jobs

### Change Monitoring

The scheduler runs a background task that:

1. Checks Redis version every 5 seconds
2. Compares with local version
3. Reloads schedule if version changed
4. Updates local aioschedule jobs

### Error Handling

- **Lock timeouts**: Automatic cleanup after 10 seconds
- **Redis failures**: Graceful degradation with logging
- **Schedule parsing errors**: Default values and error reporting

## Benefits

1. **Consistency**: Both processes always see the same schedule
2. **Real-time Updates**: Changes apply immediately across processes
3. **Reliability**: Redis persistence ensures schedule survives restarts
4. **Scalability**: Easy to add more processes reading from same Redis
5. **Debugging**: Easy to inspect schedule state in Redis

## Migration

The system automatically initializes schedule from database settings on first run, ensuring backward compatibility.

## Monitoring

Use the `/api/settings/schedule-status` endpoint to check:

- Current schedule configuration in Redis
- Schedule version number
- Process synchronization status

## Troubleshooting

### Schedule Not Updating

1. Check Redis connection: `redis-cli ping`
2. Verify schedule in Redis: `redis-cli get hn_reader:schedule:config`
3. Check scheduler logs for errors
4. Verify lock is not stuck: `redis-cli get hn_reader:schedule:lock`

### Processes Out of Sync

1. Check Redis version consistency
2. Verify change monitoring is running
3. Check for Redis connection issues
4. Review error logs for both processes

## Future Enhancements

- Schedule history tracking
- Process health monitoring
- Advanced scheduling patterns
- Webhook notifications for schedule changes
