#!/bin/bash

# This script is invoked by certbot after a certificate has been successfully provisioned or has been
# renewed successfully.

cd {{ cert_manager_path }}

pipenv run python ./deploy_cert.py --log-level '{{ cert_manager_log_level }}' --consul-certs-prefix '{{ cert_manager_consul_certs_prefix }}'
