#!/bin/sh

set -e

DIR="/app/tmp"
DUMP_FILENAME="dump_$(date +%Y%m%d_%H%M%S).sql.gz"

# make dir
if [ ! -d "$DIR" ]; then
  mkdir -p "$DIR"
fi

# make and pack DB dump
echo "Make DB dump"
PGPASSWORD=$DB_PASS pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > "$DIR/$DUMP_FILENAME"
echo "dump maked"

# upload dump to Google Drive
echo Upload dump to Google Drive
cd /scripts
python google_drive.py upload $DIR $DUMP_FILENAME
echo "dump uploaded"

# remove temp file
echo "remove temp file"
rm "$DIR/$DUMP_FILENAME"
echo "temp file removed"
