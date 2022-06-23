#!/bin/bash

TMPDIR='{{ MONGODB_SERVER_BACKUP_DIR }}'

rm -rf "$TMPDIR"
sudo -u mongodb mkdir -p "$TMPDIR"
sudo -u mongodb mongodump -u '{{ mongodb_root_admin_name }}' -p '{{ mongodb_root_admin_password }}' -o "$TMPDIR"
