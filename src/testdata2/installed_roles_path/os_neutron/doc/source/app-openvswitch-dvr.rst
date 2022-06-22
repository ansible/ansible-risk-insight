======================================
Scenario - Using Open vSwitch with DVR
======================================

Overview
~~~~~~~~

Operators can choose to utilize Open vSwitch with Distributed Virtual
Routing (DVR) instead of Linux Bridges or plain Open vSwitch for the
neutron ML2 agent. This offers the possibility to deploy virtual routing
instances outside the usual neutron networking node. This document
outlines how to set it up in your environment.

Recommended reading
~~~~~~~~~~~~~~~~~~~

This guide is a variation of the standard Open vSwitch deployment guide
available at:

`<https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-openvswitch.html>`_

We recommend that you read the following documents before proceeding:

 * Neutron documentation on Open vSwitch DVR OpenStack deployments:
   `<https://docs.openstack.org/neutron/latest/admin/deploy-ovs-ha-dvr.html>`_
 * Blog post on how OpenStack-Ansible works with Open vSwitch:
   `<https://trumant.github.io/openstack-ansible-dvr-with-openvswitch.html>`_

Prerequisites
~~~~~~~~~~~~~

Configure your networking according the Open vSwitch setup:

* Scenario - Using Open vSwitch
  `<https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-openvswitch.html>`_

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
      container_bridge: "br-provider"
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

.. note::

  The only difference a DVR deployment and the standard Open vSwitch
  deployment is the setting of the respective ``neutron_plugin_type``.

.. code-block:: yaml

  neutron_plugin_type: ml2.ovs.dvr

  neutron_ml2_drivers_type: "flat,vlan,vxlan"

The overrides are instructing Ansible to deploy the OVS mechanism driver and
associated OVS and DVR components. This is done by setting ``neutron_plugin_type``
to ``ml2.ovs.dvr``.

The ``neutron_ml2_drivers_type`` override provides support for all common type
drivers supported by OVS.

For additional information regarding provider network overrides and other
configuration options, please refer to the standard Open vSwitch deployment
available at:

`<https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-openvswitch.html>`_
