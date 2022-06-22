#### Ansible systemd_mount

This Ansible role configures systemd mount files.

This role requires the ``ansible-config_template`` collection to be available
on your local system.

To get collection you can use use the ``ansible-galaxy`` command on the
``requirements.yml`` file.. You need to install collection **before**
running this role.

``` bash
# ansible-galaxy install -r requirements.yml
```

Release notes for the project can be found at:
  https://docs.openstack.org/releasenotes/ansible-role-systemd_mount

----

###### Example playbook

> See the "defaults.yml" file for a full list of all available options.

``` yaml
- name: Create a systemd mount file for Mount1 and 2
  hosts: localhost
  become: true
  roles:
    - role: "systemd_mount"
      systemd_mounts:
        - what: '/var/lib/machines.raw'
          where: '/var/lib/machines'
          type: 'btrfs'
          options: 'loop'
          unit:
            ConditionPathExists:
              - '/var/lib/machines.raw'
          state: 'started'
          enabled: true
        - config_overrides: {}
          what: "10.1.10.1:/srv/nfs"
          where: "/var/lib/glance/images"
          type: "nfs"
          options: "_netdev,auto"
          unit:
            After:
              - network.target
```
