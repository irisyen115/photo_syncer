#!/bin/sh
docker exec google-photos python3 /app/tools/photo_sync.py >> /var/log/myscript.log 2>&1
