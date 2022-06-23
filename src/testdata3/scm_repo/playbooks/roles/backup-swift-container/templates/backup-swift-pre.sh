#!/usr/bin/env bash

# Exits after first failure
set -e

timestamp=$(date +%Y%m%dT%H:%M:%S)
source "{{ BACKUP_SWIFT_RC_DEST }}"

# swift client bundled with ubuntu has no -D option, so we have to cd into target directory
cd "{{ BACKUP_SWIFT_LOCAL_DIR }}"
/usr/bin/swift stat "{{ BACKUP_SWIFT_CONTAINER }}" > metadata
mkdir -p contents
cd contents
/usr/bin/swift download  "{{ BACKUP_SWIFT_CONTAINER }}"
