#!/usr/bin/env bash


# Exits after first failure
set -e

TMPDIR="{{ MYSQL_SERVER_BACKUP_DIR }}"
timestamp=$(date +%Y%m%dT%H:%M:%S)

rm -rf "${TMPDIR}"
mkdir -p "${TMPDIR}"
mysql -s -e 'show databases' --skip-column-names | grep -v performance_schema | grep -v information_schema | while read DBNAME; do mysqldump -uroot --complete-insert --events --single-transaction "${DBNAME}" > "${TMPDIR}/${DBNAME}".sql; done
