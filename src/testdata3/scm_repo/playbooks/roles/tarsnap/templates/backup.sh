#!/usr/bin/env bash

{% if TARSNAP_BACKUP_GLOBAL_LOCK %}
# Acquire backup lock using this script itself as the lockfile. If another
# backup task is already running, then exit immediately.
exec 200<$0
flock -n 200 || { echo "Another backup task is already running."; exit 1; }
{% endif %}

# Logic is as follows:

# 1. If pre-script fails exit immediately
# 2. Proceed if backup
# 3. Irrespective whether backup succeeds execute post-script.

timestamp=$(date -Isecond)
echo "Starting at $timestamp"

{% if TARSNAP_BACKUP_PRE_SCRIPT %}
{{ TARSNAP_BACKUP_PRE_SCRIPT }} || exit 1
{% endif %}

# We run --fsck before backup, so in case of any inconsistencies (that might happen)
# backups will still work

/usr/local/bin/tarsnap --fsck --keyfile "{{ TARSNAP_KEY_REMOTE_LOCATION }}" \
--cachedir "{{ TARSNAP_CACHE }}" && \
/usr/local/bin/tarsnap -c --keyfile "{{ TARSNAP_KEY_REMOTE_LOCATION }}" \
--cachedir "{{ TARSNAP_CACHE }}"  -f "{{ TARSNAP_ARCHIVE_NAME }}-${timestamp}" \
{{ TARSNAP_BACKUP_FOLDERS }} {% if TARSNAP_BACKUP_SNITCH %} && curl -sS {{ TARSNAP_BACKUP_SNITCH }} {% endif %}

{% if TARSNAP_BACKUP_POST_SCRIPT %}{{ TARSNAP_BACKUP_POST_SCRIPT }}{% endif %}

timestamp=$(date -Isecond)
echo "Finishing at $timestamp"
