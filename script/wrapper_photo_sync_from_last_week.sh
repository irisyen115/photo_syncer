#!/bin/sh
docker exec google-photos python3 /app/tools/photo_sync_from_last_week.py >> /var/log/myscript4.log 2>&1
