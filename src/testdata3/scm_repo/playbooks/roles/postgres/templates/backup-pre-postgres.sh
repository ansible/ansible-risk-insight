#!/bin/bash

TMPDIR="{{ POSTGRES_SERVER_BACKUP_DIR }}"

rm -rf "$TMPDIR"
mkdir -p "$TMPDIR"
pg_dumpall -U postgres --globals > "$TMPDIR/postgresql_globals.sql"
psql -U postgres -t -c "SELECT datname FROM pg_database WHERE datistemplate = false;" |
    xargs -n 1 -I {} pg_dump -U postgres --format=directory --file="$TMPDIR/{}" {}
