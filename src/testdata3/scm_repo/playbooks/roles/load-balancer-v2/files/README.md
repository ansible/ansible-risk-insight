# Client-provided SSL certificates

This directory contains manually generated certificates that can be served for sites we host.
During provision of load balancers they will be decrypted and placed in `/etc/haproxy/certs/` directory
of every HAProxy instance.

## Adding new certs

1. Copy certificates in directory with the name of environment you want to add them for (e.g., `stage`, `prod`).
1. Encrypt them. `ansible-vault encrypt clients.new.cert.pem` Use the [right password](https://vault.opencraft.com:8200/ui/vault/secrets/secret/show/core/Ansible%20Vault).
1. Encode the filename. `echo -n "clients.new.cert" | base64`
1. Rename the file. Ensure no "/"s in the filename. Ensure file ends with `.pem`
1. Run the playbook. `ansible-playbook -v deploy/playbooks/load-balancer-v2.yml -l haproxy-<...>.net.opencraft.hosting`