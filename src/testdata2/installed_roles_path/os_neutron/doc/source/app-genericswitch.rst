========================================
Scenario - Networking Generic Switch
========================================

Overview
~~~~~~~~

Operators can choose to utilize the Networking Generic Switch (NGS) mechanism
driver to manage physical switches when Ironic is integrated with Neutron.
The Networking Generic Switch mechanism driver can be deployed alongside other
drivers, such as Open vSwitch or LinuxBridge. This document outlines how to
set it up in your environment.

Recommended reading
~~~~~~~~~~~~~~~~~~~

It is recommended to familiarize yourself with project-specific documentation
to better understand deployment and configuration options:

* `Networking Generic Switch <https://docs.openstack.org/networking-generic-switch/latest/>`_

Prerequisites
~~~~~~~~~~~~~

* `Ironic Bare-Metal Provisioning Service <https://github.com/openstack/openstack-ansible-os_ironic>`_

* `Supported Network Hardware <https://docs.openstack.org/networking-generic-switch/latest/supported-devices.html>`_

* Network connectivity from the node(s) running the `neutron-server` service
  to the management interface of the physical switch(es) connected to
  Ironic bare-metal nodes. This is outside the scope of OpenStack-Ansible.

OpenStack-Ansible user variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add ``ml2.genericswitch`` to the ``neutron_plugin_types`` list in
``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

  neutron_plugin_types:
  - ml2.genericswitch

To interface with a supported network switch, configure ini overrides for each
connected switch in your environment:

.. code-block:: yaml

  neutron_ml2_conf_genericswitch_ini_overrides:
    genericswitch:arista01:
      device_type: netmiko_arista_eos
      ngs_mac_address: "00:1c:73:29:ea:ca"
      ip: "192.168.90.2"
      username: "openstack"
      password: "0p3nst@ck"
      ngs_port_default_vlan: 3
    genericswitch:arista02:
      device_type: netmiko_arista_eos
      ngs_mac_address: "00:1c:73:29:ea:cb"
      ip: "192.168.90.3"
      username: "openstack"
      password: "0p3nst@ck"
      ngs_port_default_vlan: 3

Lastly, configure an override to Ironic to enable the ``neutron`` interface:

.. code-block:: console

  ironic_enabled_network_interfaces_list: neutron
  ironic_default_network_interface: neutron

Notes
~~~~~

Ironic bare-metal ports that are associated with bare-metal nodes can be
configured with the respective connection details using the
``openstack baremetal port set`` command:

.. code-block:: console

  openstack baremetal port set 3a948c3b-6c41-4f68-8389-c4f5ca667c63 \
  --local-link-connection switch_info=arista01 \
  --local-link-connection switch_id="00:1c:73:29:ea:ca" \
  --local-link-connection port_id="et11"

When a server is deployed using a bare-metal node, Neutron will connect to
the respective switch(es) and configure the switchport interface(s) according.
