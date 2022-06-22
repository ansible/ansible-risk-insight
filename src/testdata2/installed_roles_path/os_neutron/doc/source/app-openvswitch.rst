=============================
Scenario - Using Open vSwitch
=============================

Overview
~~~~~~~~

Operators can choose to utilize Open vSwitch instead of Linux Bridges for the
neutron ML2 agent. This offers different capabilities and integration points
with neutron. This document outlines how to set it up in your environment.

Recommended reading
~~~~~~~~~~~~~~~~~~~

We recommend that you read the following documents before proceeding:

* Neutron documentation on Open vSwitch OpenStack deployments:
  `<https://docs.openstack.org/liberty/networking-guide/scenario-classic-ovs.html>`_
* Blog post on how OpenStack-Ansible works with Open vSwitch:
  `<https://medium.com/@travistruman/configuring-openstack-ansible-for-open-vswitch-b7e70e26009d>`_

Prerequisites
~~~~~~~~~~~~~

All compute nodes must have bridges configured:

- ``br-mgmt``
- ``br-vlan`` (optional - used for vlan networks)
- ``br-vxlan`` (optional - used for vxlan tenant networks)
- ``br-storage`` (optional - used for certain storage devices)

For more information see:
`<https://docs.openstack.org/project-deploy-guide/openstack-ansible/newton/targethosts-networkconfig.html>`_

These bridges may be configured as either a Linux Bridge (which would connect
to the Open vSwitch controlled by neutron) or as an Open vSwitch.

Configuring bridges (Linux Bridge)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following is an example of how to configure a bridge (example: ``br-mgmt``)
with a Linux Bridge on Ubuntu 16.04 LTS:

``/etc/network/interfaces``

.. code-block:: shell-session

    auto lo
    iface lo inet loopback

    # Management network
    auto eth0
    iface eth0 inet manual

    # VLAN network
    auto eth1
    iface eth1 inet manual

    source /etc/network/interfaces.d/*.cfg

``/etc/network/interfaces.d/br-mgmt.cfg``

.. code-block:: shell-session

    # OpenStack Management network bridge
    auto br-mgmt
    iface br-mgmt inet static
      bridge_stp off
      bridge_waitport 0
      bridge_fd 0
      bridge_ports eth0
      address MANAGEMENT_NETWORK_IP
      netmask 255.255.255.0

One ``br-<type>.cfg`` is required for each bridge. VLAN interfaces can be used
to back the ``br-<type>`` bridges if there are limited physical adapters on the
system.

Configuring bridges (Open vSwitch)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Another configuration method routes everything with Open vSwitch. The bridge
(example: ``br-mgmt``) can be an Open vSwitch itself.

The following is an example of how to configure a bridge (example: ``br-mgmt``)
with Open vSwitch on Ubuntu 16.04 LTS: *

``/etc/network/interfaces``

.. code-block:: shell-session

    auto lo
    iface lo inet loopback

    source /etc/network/interfaces.d/*.cfg

    # Management network
    allow-br-mgmt eth0
    iface eth0 inet manual
      ovs_bridge br-mgmt
      ovs_type OVSPort

    # VLAN network
    allow-br-vlan eth1
    iface eth1 inet manual
      ovs_bridge br-vlan
      ovs_type OVSPort

``/etc/network/interfaces.d/br-mgmt.cfg``

.. code-block:: shell-session

    # OpenStack Management network bridge
    auto br-mgmt
    allow-ovs br-mgmt
    iface br-mgmt inet static
      address MANAGEMENT_NETWORK_IP
      netmask 255.255.255.0
      ovs_type OVSBridge
      ovs_ports eth0

One ``br-<type>.cfg`` is required for each bridge. VLAN interfaces can be used
to back the ``br-<type>`` bridges if there are limited physical adapters on the
system.

**Warning**: There is a bug in Ubuntu 16.04 LTS where the Open vSwitch service
won't start properly when using systemd. The bug and workaround are discussed
here: `<http://www.opencloudblog.com/?p=240>`_


OpenStack-Ansible user variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Create a group var file for your network hosts
``/etc/openstack_deploy/group_vars/network_hosts``. It has to include:

.. code-block:: yaml

  # Ensure the openvswitch kernel module is loaded
  openstack_host_specific_kernel_modules:
    - name: "openvswitch"
      pattern: "CONFIG_OPENVSWITCH"

Specify provider network definitions in your
``/etc/openstack_deploy/openstack_user_config.yml`` that define
one or more Neutron provider bridges and related configuration:

.. note::

  Bridges specified here will be created automatically. If
  ``network_interface`` is defined, the interface will be placed into
  the bridge automatically.

.. code-block:: yaml

  - network:
      container_bridge: "br-provider"
      container_type: "veth"
      type: "vlan"
      range: "101:200,301:400"
      net_name: "physnet1"
      network_interface: "bond1"
      group_binds:
        - neutron_openvswitch_agent
  - network:
      container_bridge: "br-provider2"
      container_type: "veth"
      type: "vlan"
      range: "203:203,467:500"
      net_name: "physnet2"
      network_interface: "bond2"
      group_binds:
        - neutron_openvswitch_agent

When using ``flat`` provider networks, modify the network type accordingly:

.. code-block:: yaml

  - network:
      container_bridge: "br-publicnet"
      container_type: "veth"
      type: "flat"
      net_name: "flat"
      group_binds:
        - neutron_openvswitch_agent

Specify an overlay network definition in your
``/etc/openstack_deploy/openstack_user_config.yml`` that defines
overlay network-related configuration:

.. note::

  The bridge name should correspond to a pre-created Linux bridge or
  OVS bridge.

.. code-block:: yaml

  - network:
      container_bridge: "br-vxlan"
      container_type: "veth"
      container_interface: "eth10"
      ip_from_q: "tunnel"
      type: "vxlan"
      range: "1:1000"
      net_name: "vxlan"
      group_binds:
        - neutron_openvswitch_agent

Set the following user variables in your
``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

  neutron_plugin_type: ml2.ovs

  neutron_ml2_drivers_type: "flat,vlan,vxlan"

The overrides are instructing Ansible to deploy the OVS mechanism driver and
associated OVS components. This is done by setting ``neutron_plugin_type``
to ``ml2.ovs``.

The ``neutron_ml2_drivers_type`` override provides support for all common type
drivers supported by OVS.

If provider network overrides are needed on a global or per-host basis,
the following format can be used in ``user_variables.yml`` or per-host
in ``openstack_user_config.yml``.

.. note::

  These overrides are not normally required when defining global provider
  networks in the ``openstack_user_config.yml`` file.

.. code-block:: yaml

  # When configuring Neutron to support vxlan tenant networks and
  # vlan provider networks the configuration may resemble the following:
  neutron_provider_networks:
    network_types: "vxlan"
    network_vxlan_ranges: "1:1000"
    network_vlan_ranges: "physnet1:102:199"
    network_mappings: "physnet1:br-provider"
    network_interface_mappings: "br-provider:bond1"

  # When configuring Neutron to support only vlan tenant networks and
  # vlan provider networks the configuration may resemble the following:
  neutron_provider_networks:
    network_types: "vlan"
    network_vlan_ranges: "physnet1:102:199"
    network_mappings: "physnet1:br-provider"
    network_interface_mappings: "br-provider:bond1"

  # When configuring Neutron to support multiple vlan provider networks
  # the configuration may resemble the following:
  neutron_provider_networks:
    network_types: "vlan"
    network_vlan_ranges: "physnet1:102:199,physnet2:2000:2999"
    network_mappings: "physnet1:br-provider,physnet2:br-provider2"
    network_interface_mappings: "br-provider:bond1,br-provider2:bond2"

  # When configuring Neutron to support multiple vlan and flat provider
  # networks the configuration may resemble the following:
  neutron_provider_networks:
    network_flat_networks: "*"
    network_types: "vlan"
    network_vlan_ranges: "physnet1:102:199,physnet2:2000:2999"
    network_mappings: "physnet1:br-provider,physnet2:br-provider2"
    network_interface_mappings: "br-provider:bond1,br-provider2:bond2"

Open Virtual Switch (OVS) commands
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following commands can be used to provide useful information about the
state of Open vSwitch networking and configurations.

The ``ovs-vsctl show`` command provides information about the virtual switches
and connected ports currently configured on the host:

.. code-block:: console

  root@infra01:~# ovs-vsctl show
  4ef304ff-b803-4d09-95f5-59a076323949
      Manager "ptcp:6640:127.0.0.1"
          is_connected: true
      Bridge br-int
          Controller "tcp:127.0.0.1:6633"
              is_connected: true
          fail_mode: secure
          Port "tap2e7e0507-e4"
              tag: 2
              Interface "tap2e7e0507-e4"
                  type: internal
          Port int-br-vlan
              Interface int-br-vlan
                  type: patch
                  options: {peer=phy-br-provider}
          Port br-int
              Interface br-int
                  type: internal
          Port "tap7796ab3d-e9"
              tag: 5
              Interface "tap7796ab3d-e9"
                  type: internal
          Port patch-tun
              Interface patch-tun
                  type: patch
                  options: {peer=patch-int}
      Bridge br-tun
          Controller "tcp:127.0.0.1:6633"
              is_connected: true
          fail_mode: secure
          Port "vxlan-ac1df015"
              Interface "vxlan-ac1df015"
                  type: vxlan
                  options: {df_default="true", in_key=flow, local_ip="172.29.240.20", out_key=flow, remote_ip="172.29.240.21"}
          Port patch-int
              Interface patch-int
                  type: patch
                  options: {peer=patch-tun}
          Port "vxlan-ac1df017"
              Interface "vxlan-ac1df017"
                  type: vxlan
                  options: {df_default="true", in_key=flow, local_ip="172.29.240.20", out_key=flow, remote_ip="172.29.240.23"}
          Port br-tun
              Interface br-tun
                  type: internal
      Bridge br-provider
          Controller "tcp:127.0.0.1:6633"
              is_connected: true
          fail_mode: secure
          Port "ens192"
              Interface "ens192"
          Port br-provider
              Interface br-provider
                  type: internal
          Port phy-br-provider
              Interface phy-br-provider
                  type: patch
                  options: {peer=int-br-provider}
      ovs_version: "2.10.0"

Additional commands can be found in upstream Open vSwitch documentation.

Notes
~~~~~

The ``neutron-openvswitch-agent`` service will check in as an agent
and can be observed using the ``openstack network agent list`` command:

.. code-block:: console

  root@infra01-utility-container-ce1509fd:~# openstack network agent list --agent-type open-vswitch
  +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
  | ID                                   | Agent Type         | Host        | Availability Zone | Alive | State | Binary                    |
  +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
  | 4dcef710-ec0c-4925-a940-dc319cd6849f | Open vSwitch agent | compute03   | None              | :-)   | UP    | neutron-openvswitch-agent |
  | 5e1f8670-b90e-49c3-84ff-e981aeccb171 | Open vSwitch agent | compute02   | None              | :-)   | UP    | neutron-openvswitch-agent |
  | 78746672-d77a-4d8a-bb48-f659251fa246 | Open vSwitch agent | compute01   | None              | :-)   | UP    | neutron-openvswitch-agent |
  | eebab5da-3ef5-4582-84c5-f29e2472a44a | Open vSwitch agent | infra01     | None              | :-)   | UP    | neutron-openvswitch-agent |
  +--------------------------------------+--------------------+-------------+-------------------+-------+-------+---------------------------+
