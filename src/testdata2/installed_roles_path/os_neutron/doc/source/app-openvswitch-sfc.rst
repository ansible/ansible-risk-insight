======================================
Scenario - Using Open vSwitch with SFC
======================================

Overview
~~~~~~~~

Operators can choose to configure SFC mechanism with Open vSwitch
instead of ODL through the neutron networking-sfc project. The SFC
configuration results in OVS flows being configured with SFC
specifics using MPLS as dataplane technology. This document
outlines how to set it up in your environment.

Recommended reading
~~~~~~~~~~~~~~~~~~~

We recommend that you read the following documents before proceeding:

 * General overview of neutron networking-sfc:
   `<https://docs.openstack.org/networking-sfc/latest/index.html>`_
 * How to configure networking-sfc in neutron:
   `<https://docs.openstack.org/networking-sfc/latest/install/configuration.html>`_

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

Set the following user variables in your
``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

  ### neutron specific config
  neutron_plugin_type: ml2.ovs

  neutron_ml2_drivers_type: "flat,vlan"

  neutron_plugin_base:
   - router
   - metering
   - flow_classifier
   - sfc

  # Typically this would be defined by the os-neutron-install
  # playbook. The provider_networks library would parse the
  # provider_networks list in openstack_user_config.yml and
  # generate the values of network_types, network_vlan_ranges
  # and network_mappings. network_mappings would have a
  # different value for each host in the inventory based on
  # whether or not the host was metal (typically a compute host)
  # or a container (typically a neutron agent container)
  #
  # When using Open vSwitch, we override it to take into account
  # the Open vSwitch bridge we are going to define outside of
  # OpenStack-Ansible plays
  neutron_provider_networks:
    network_flat_networks: "*"
    network_types: "vlan"
    network_vlan_ranges: "physnet1:102:199"
    network_mappings: "physnet1:br-provider"

**Note:** The only difference to the Standard Open vSwitch configuration
is the setting of the ``neutron_plugin_base``.
