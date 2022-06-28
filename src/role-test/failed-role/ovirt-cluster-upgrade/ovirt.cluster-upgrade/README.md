oVirt Cluster Upgrade
=========

The `ovirt.cluster-upgrade` role iterates through all the hosts in a cluster and upgrades them.

Note
----
Please note that when installing this role from Ansible Galaxy you are instructed to run following command:

```bash
$ ansible-galaxy install ovirt.cluster-upgrade
```

This will download the role to the directory with the same name as you specified on the
command line, in this case `ovirt.cluster-upgrade`. But note that it is case sensitive, so if you specify
for example `OVIRT.cluster-upgrade` it will download the same role, but it will add it to the directory named
`OVIRT.cluster-upgrade`, so you later always have to use this role with upper case prefix. So be careful how
you specify the name of the role on command line.

For the RPM installation we install three legacy names `ovirt.cluster-upgrade`, `oVirt.cluster-upgrade` and `ovirt-cluster-upgrade`.
So you can use any of this name. This documentation and examples in this repository are using name `ovirt.cluster-upgrade`.
`oVirt.cluster-upgrade` and `ovirt-cluster-upgrade` role names are deprecated.

Requirements
------------

 * Ansible version 2.9 or higher
 * Python SDK version 4.3 or higher

Role Variables
--------------

| Name                    | Default value         |                                                     |
|-------------------------|-----------------------|-----------------------------------------------------|
| cluster_name            | Default               | Name of the cluster to be upgraded.                 |
| stopped_vms             | UNDEF                 | List of virtual machines to stop before upgrading.      |
| stop_non_migratable_vms <br/> <i>alias: stop_pinned_to_host_vms</i>  | false                 | Specify whether to stop virtual machines pinned to the host being upgraded. If true, the pinned non-migratable virtual machines will be stopped and host will be upgraded, otherwise the host will be skipped. |
| upgrade_timeout         | 3600                  | Timeout in seconds to wait for host to be upgraded. |
| host_statuses           | [UP]                  | List of host statuses. If a host is in any of the specified statuses then it will be upgraded. |
| host_names              | [\*]                  | List of host names to be upgraded.        |
| check_upgrade           | false                 | If true, run check_for_upgrade action on all hosts before executing upgrade on them. If false, run upgrade only for hosts with available upgrades and ignore all other hosts. |
| reboot_after_upgrade    | true                  | If true reboot hosts after successful upgrade. |
| use_maintenance_policy  | true                  | If true the cluster policy will be switched to cluster_maintenance during upgrade otherwise the policy will be unchanged. |
| healing_in_progress_checks            | 6                     | Maximum number of attempts to check if gluster healing is still in progress. |
| healing_in_progress_check_delay              | 300                   | The delay in seconds between each attempt to check if gluster healing is still in progress.    |
| wait_to_finish_healing  | 5                     | Delay in minutes to wait to finish gluster healing process after successful host upgrade.             |

Dependencies
------------

No.

Example Playbook
----------------

```yaml
---
- name: oVirt infra
  hosts: localhost
  connection: local
  gather_facts: false

  vars:
    engine_fqdn: ovirt-engine.example.com
    engine_user: admin@internal
    engine_password: 123456
    engine_cafile: /etc/pki/ovirt-engine/ca.pem

    cluster_name: production
    stopped_vms:
      - openshift-master-0
      - openshift-node-0
      - openshift-node-image

  roles:
    - ovirt.cluster-upgrade
```

[![asciicast](https://asciinema.org/a/122760.png)](https://asciinema.org/a/122760)

License
-------

Apache License 2.0
