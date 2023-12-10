#!/bin/sh

set -e

python core/wait_for_db.py

# start the backup script in the background
if [ "$DEV" != "true" ]; then
  (
    while true; do
      cd /scripts
      ./dump_db.sh || true
      sleep 86400
    done
  ) &
fi
cd /app

alembic upgrade head

exec python main.py
