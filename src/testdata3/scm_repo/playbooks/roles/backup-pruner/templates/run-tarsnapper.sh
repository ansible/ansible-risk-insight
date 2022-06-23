#!/usr/bin/env bash

# Ensure that tarsnap is accessible on the path when running as a
# GNU Parallel task
PATH=$PATH:/usr/local/bin

KEY_FILE="/etc/tarsnap/{{ item.name }}.key"
CACHE_DIR="/var/cache/tarsnap/{{ item.name }}"

/usr/local/bin/tarsnap --fsck --keyfile ${KEY_FILE} \
 --cachedir ${CACHE_DIR} && \
/usr/local/bin/tarsnapper \
 -o keyfile ${KEY_FILE} -o cachedir  ${CACHE_DIR} \
 --target '{{ item.target }}' --deltas {{ item.deltas }} \
 - "$@"
# NOTE: '' around {{ item.target }} are necessary as
#       it can contain $date which should not be expanded
#       by bash
# NOTE: There are no quotes around deltas as tarsnap uses
#       shell to tokenize them.
# NOTE: single hyphen before "$@" is necessary
