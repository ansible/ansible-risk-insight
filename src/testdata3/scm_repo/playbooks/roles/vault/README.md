# Ansible Role for Vault

The following are the steps needed in getting a Vault server up and running.

It's unfortunately not as simple as running this playbook, because
due to the nature of Vault, some explicitly manual steps are required
to initialize and unseal the system, which would be too difficult to get right with Ansible alone.

We assume you've already configured the variables correctly.

1. Run this vault playbook.
1. SSH into the Vault server that will also manage policies, and run:

    ```bash
    sudo -s

    # You'll get back a master token and 5 unseal keys.
    # Only 3 unseal keys are needed to regenerate the master token.
    # You can arbitrarily change the total keys and/or unseal keys available with CLI options.
    vault operator init

    # By default we only need 3 unseal keys, so unseal Vault using 3 of them now.
    vault operator unseal -> provide 1 unique unseal key
    vault operator unseal -> provide 1 unique unseal key
    vault operator unseal -> provide 1 unique unseal key

    # Need to be root to bootstrap.
    vault login -token-only -> provide root token

    # First things first: log everything from hereon.
    vault audit enable file file_path=/var/log/vault/audit.log
    ```

1. Run the `vault-policy` playbook with `-e "vault_policy_mgmt_token=<root-token>"` appended
1. Run the following to bootstrap the remaining features:

    ```bash
    # Enable GitHub auth and link them to an org.
    # Here, we show an example of linking to OpenCraft and using the Core team against a "core-team" policy we created through `vault_policies`.
    # See the `vault-policy` playbook for more details.
    vault auth enable github
    vault write auth/github/config organization=open-craft
    vault write auth/github/map/teams/core value=full-secret,add-github-users,policy-management
    vault write auth/github/map/teams/accounting-billing value=full-accounting

    # Use the token created from this as the `vault_policy_mgmt_token` going forward.
    # It needs to be an orphan, because if you happen to revoke the master key, all children
    # keys, including this one, will get revoked, and you'll be forced to regenerate
    # the master key to do anything at the system level anymore.
    vault token create -ttl=87600h -policy=policy-management -orphan

    # Once we revoke this token, there are many system operations we can no longer do unless we re-generate it.
    # Up to you if you want to do this.
    vault token revoke <root-token>
    ```

1. To wrap up, unseal the remaining servers. SSH in to each and run the same `vault operator unseal` commands, with the same unseal keys if you like.
