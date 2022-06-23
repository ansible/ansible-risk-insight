#!/bin/bash

# This script watches a Consul KV path that is used to detect whether we need
# to re-request certificates.
#
# Specifically it watches the key prefix defined by `cert_manager_consul_watch_prefix`.
# When any change is made to keys falling under that prefix, a lock is attempted at
# `cert_manager_consul_lock_prefix`, and once gotten, we run the certificate management
# code that will attempt to request/renew certificates.

cd {{ cert_manager_path }}

consul watch -type=keyprefix -prefix={{ cert_manager_consul_watch_prefix }} \
    "sleep {{ cert_manager_watch_delay }}; \
     consul lock {{ cert_manager_consul_lock_prefix }} \
         pipenv run python manage_certs.py {% if cert_manager_stage %}--letsencrypt-use-staging{% endif %} \
             --contact-email {{ cert_manager_email }} \
             --log-level {{ cert_manager_log_level }} \
             --webroot-path {{ cert_manager_webroot_path }} \
             --consul-ocim-prefix {{ cert_manager_consul_ocim_prefix }} \
             --consul-certs-prefix {{ cert_manager_consul_certs_prefix }} \
             {% if cert_manager_failure_alert_email %}--failure-alert-email {{ cert_manager_failure_alert_email }} \{% endif %}
             --dns-delay {{ cert_manager_dns_delay }}"
