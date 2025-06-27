#!/bin/sh
docker exec google-photos python3 /app/tools/photo_sync_from_previous.py >> /var/log/myscript3.log 2>&1
