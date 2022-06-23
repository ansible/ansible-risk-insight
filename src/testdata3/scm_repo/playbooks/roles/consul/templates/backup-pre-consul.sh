#!/usr/bin/env bash

set -e

TMPDIR="{{ consul_data_dir }}/backups"
timestamp=$(date +%Y%m%dT%H:%M:%S)

rm -rf "${TMPDIR}"
mkdir -p "${TMPDIR}"

{{ consul_bin_dir }}/consul snapshot save -token {{ consul_acl_master_token }} "${TMPDIR}/consul.snap"
