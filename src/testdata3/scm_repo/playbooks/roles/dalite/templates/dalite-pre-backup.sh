#!/usr/bin/env bash
# Will exit on first error (we want it!)
set -e

service gunicorn restart

timestamp=$(date +%Y%m%dT%H:%M:%S)

if [ -f /var/log/dalite/student.log-* ]; then
   mv /var/log/dalite/student.log-* "{{ DALITE_LOG_DOWNLOAD_LOG_DIR }}"
fi
chown "{{ DALITE_LOG_DOWNLOAD_USER }}:{{ MYSQL_DALITE_USER }}" "{{ DALITE_LOG_DOWNLOAD_LOG_DIR }}" "{{ DALITE_LOG_DOWNLOAD_DB_DIR }}"
chmod g+rwx "{{ DALITE_LOG_DOWNLOAD_LOG_DIR }}" "{{ DALITE_LOG_DOWNLOAD_DB_DIR }}"
sudo -u "{{ MYSQL_DALITE_USER }}" -H {{DALITE_MANAGE_PY}} dumpdata -o "{{ DALITE_LOG_DOWNLOAD_DB_DIR }}/database-${timestamp}.json"
mysqldump -u "{{ MYSQL_DALITE_USER }}" -p'{{ MYSQL_DALITE_PASSWORD }}' -h "{{ MYSQL_DALITE_HOST }}" "{{ MYSQL_DALITE_DATABASE }}" -r "{{ DALITE_LOG_DOWNLOAD_DB_DIR }}/database-${timestamp}.sql"
gzip "{{ DALITE_LOG_DOWNLOAD_LOG_DIR }}"/* "{{ DALITE_LOG_DOWNLOAD_DB_DIR }}"/*
chown "{{ DALITE_LOG_DOWNLOAD_USER }}:{{ DALITE_LOG_DOWNLOAD_USER }}" "{{ DALITE_LOG_DOWNLOAD_LOG_DIR }}"/* "{{ DALITE_LOG_DOWNLOAD_DB_DIR }}"/*
