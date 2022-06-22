#### Ansible systemd_networkd

This Ansible role configures systemd-networkd link, network, and netdev files.

This role requires the ``ansible-config_template`` collection to be available
on your local system.

To get collection you can use use the ``ansible-galaxy`` command on the
``requirements.yml`` file.. You need to install collection **before**
running this role.

``` bash
# ansible-galaxy install -r requirements.yml
```

Release notes for the project can be found at:
  https://docs.openstack.org/releasenotes/ansible-role-systemd_networkd


----

###### Example playbook

> See the "defaults.yml" file for a full list of all available options.

``` yaml
- name: Create a systemd-networkd interfaces
  hosts: localhost
  become: true
  roles:
    - role: "systemd_networkd"
      systemd_netdevs:
        - NetDev:
            Name: dummy0
            Kind: dummy
        - NetDev:
            Name: dummy1
            Kind: dummy
        - NetDev:
            Name: bond0
            Kind: bond
          Bond:
            Mode: 802.3ad
            TransmitHashPolicy: layer3+4
            MIIMonitorSec: 1s
            LACPTransmitRate: fast
        - NetDev:
            Name: br-dummy
            Kind: bridge
      systemd_networks:
        - interface: "dummy0"
          bond: "bond0"
          mtu: 9000
        - interface: "dummy1"
          bond: "bond0"
          mtu: 9000
        - interface: "bond0"
          bridge: "br-dummy"
          mtu: 9000
        - interface: "br-dummy"
          address: "10.0.0.100"
          netmask: "255.255.255.0"
          gateway: "10.0.0.1"
          mtu: 9000
          usedns: true
          static_routes:
            - gateway: "10.1.0.1"
              cidr: "10.1.0.0/24"
          config_overrides:
            Network:
              ConfigureWithoutCarrier: true
```
