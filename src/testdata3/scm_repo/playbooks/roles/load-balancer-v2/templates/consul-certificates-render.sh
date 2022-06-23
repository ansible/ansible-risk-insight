#!/bin/bash

consul watch -type=keyprefix -prefix={{ haproxy_consul_certs_prefix }} \
    consul lock {{ haproxy_consul_lock_prefix }} \
        'rm -f /etc/haproxy/certs/ocim/* && consul kv get -keys {{ haproxy_consul_certs_prefix }}/ | { while read -r key; do consul kv get "$key" > "/etc/haproxy/certs/ocim/${key##*/}"; done; } && flock -n -E 0 /tmp/haproxy-reload-lock service haproxy reload'
