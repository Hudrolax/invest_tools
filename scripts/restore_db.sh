#!/bin/sh

set -e

FILE_ID="$1"
DIR="/app/tmp"
DUMP_FILE="dump.sql.gz"

# download dump from Google Drive
python google_drive.py download $DIR $FILE_ID

# Удаление существующей базы данных
PGPASSWORD=$DB_PASS dropdb -h $DB_HOST -U $DB_USER $DB_NAME

# Создание новой базы данных
PGPASSWORD=$DB_PASS createdb -h $DB_HOST -U $DB_USER $DB_NAME

# Распаковка дампа и загрузка в базу данных
gunzip -c "$DIR/$DUMP_FILE" | PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $DB_NAME

echo "Dump file loaded to $DB_NAME success!"
rm "$DIR/$DUMP_FILE"
echo "dump $DIR/$DUMP_FILE removed."
