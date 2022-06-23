#!/bin/sh

# This script watches a Consul KV path that is used to gather data needed
# for rendering HAProxy's several configuration files.

consul watch -type=keyprefix -prefix={{ haproxy_consul_watch_prefix }} \
    consul lock {{ haproxy_consul_lock_prefix }} \
        consul-template -once -config /etc/consul-template/config
