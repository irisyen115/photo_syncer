#!/bin/sh

start_time=$(date +%s)
docker exec google-photos python3 /app/tools/photo_sync_from_previous.py >> /var/log/myscript3.log 2>&1
status=$?
end_time=$(date +%s)
duration=$((end_time - start_time))

TEXTFILE_PATH="/volume1/src/photo_syncer/textfile/photo_sync.prom"

if [ "$status" -eq 0 ]; then
    success=1
else
    success=0
fi

cat <<EOF > "$TEXTFILE_PATH"
# HELP photo_sync_last_run_timestamp_seconds Unix timestamp of the last photo sync run
# TYPE photo_sync_last_run_timestamp_seconds gauge
photo_sync_last_run_timestamp_seconds $end_time
# HELP photo_sync_last_run_duration_seconds Duration in seconds of the last photo sync run
# TYPE photo_sync_last_run_duration_seconds gauge
photo_sync_last_run_duration_seconds $duration
# HELP photo_sync_last_run_success Was the last run successful (1=success, 0=failure)
# TYPE photo_sync_last_run_success gauge
photo_sync_last_run_success $success
EOF
