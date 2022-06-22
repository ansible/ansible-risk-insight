========================================
Scenario - VMware NSX Plugin
========================================

Introduction
~~~~~~~~~~~~

This document covers the steps to integrate the VMware NSX plugin with
OpenStack Ansible.

.. warning::

  Currently, only NSX-T Policy API is supported.

Please follow these steps:

- Configure Neutron to use the NSX plugin

Prerequisites
~~~~~~~~~~~~~

#. The deployment environment is configured according to OSA best
   practices such as cloning OSA software and bootstrapping Ansible.
   See `OpenStack-Ansible Install Guide
   <https://docs.openstack.org/project-deploy-guide/openstack-ansible/latest/>`_.

#. NSX-T has been deployed per its installation guide and compute nodes have
   been properly configured as transport nodes. See
   `NSX-T Data Center Installation Guide
   <https://docs.vmware.com/en/VMware-NSX-T-Data-Center/3.0/installation/GUID-3E0C4CEC-D593-4395-84C4-150CD6285963.htm>` _.

Configure Neutron to use the NSX plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Copy the neutron environment overrides to
``/etc/openstack_deploy/env.d/neutron.yml`` and disable agent creation, since
it is not needed.

.. code-block:: yaml

  neutron_agents_container:
    belongs_to:
      - network_containers
    contains: { }

Copy the nova environment overrides to
``/etc/openstack_deploy/env.d/nova.yml`` and disable neutron agent creation,
since it is not needed.

.. code-block:: yaml

  container_skel:
    nova_api_container:
      belongs_to:
        - compute-infra_containers
        - os-infra_containers
      contains:
        - nova_api_metadata
        - nova_api_os_compute
        - nova_conductor
        - nova_scheduler
        - nova_console
    nova_compute_container:
      belongs_to:
        - compute_containers
        - kvm-compute_containers
        - qemu-compute_containers
      contains:
        - nova_compute
      properties:
        is_metal: true

Set the following required variables in your
``/etc/openstack_deploy/user_variables.yml``

.. code-block:: yaml

  neutron_plugin_type: vmware.nsx
  nova_network_type: nsx
  nsx_api_password: <password>
  nsx_api_managers:
    - nsx-manager-01
    - nsx-manager-02
    - nsx-manager-03

Optionally specify additional parameters using overrides

.. code-block:: yaml

  neutron_nsx_conf_ini_overrides:
    nsx_p:
      default_tier0_router: my-tier0-router
      default_overlay_tz: my-overlay-tz
      default_vlan_tz: my-vlan-tz
      metadata_proxy: my-metadata-proxy-profile
      dhcp_profile: my-dhcp-profile

.. warning::

  If NSX has defined more than one tier 0, overlay/vlan tz, metadata proxy, or
  dhcp profile, then you must explicitly define those using conf overrides.
  Neutron will fail to start if these are not defined in those conditions.

Installation
~~~~~~~~~~~~

After the environment has been configured as detailed above, start the
OpenStack deployment as listed in the OpenStack-Ansible Install Guide.
