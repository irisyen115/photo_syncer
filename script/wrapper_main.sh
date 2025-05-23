#!/bin/sh
if [ $(( $(date +%s) / 86400 % 7 )) -eq 0 ]; then
    /usr/bin/python3 /root/Upload_goole_photos-/main.py >> /var/log/myscript.log 2>&1
fi
