=====================================================
Scenario - Using the networking-calico Neutron plugin
=====================================================

Introduction
~~~~~~~~~~~~

This document describes the steps required to deploy Project Calico Neutron
networking with OpenStack-Ansible (OSA). These steps include:

- Configure OSA environment overrides.

- Configure OSA user variables.

- Execute the playbooks.

For additional configuration about Project Calico and its architecture, please
reference the `networking-calico`_ and `Project Calico`_ documentation.

.. _networking-calico: https://docs.openstack.org/networking-calico/latest/
.. _Project Calico: https://docs.projectcalico.org/en/latest/index.html

Prerequisites
~~~~~~~~~~~~~

#. The deployment environment has been configured according to OSA
   best-practices. This includes cloning OSA software and bootstrapping
   Ansible. See `OpenStack-Ansible Install Guide <index.html>`_
#. BGP peers configured to accept routing announcements from your hypervisors.
   By default, the hypervisor's default router is set as the BGP peer.

Configure OSA Environment for Project Calico
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Add hosts to the ``/etc/openstack_deploy/conf.d/etcd.conf`` configuration file
to add container hosts for the etcd cluster. See
``etc/openstack_deploy/conf.d/etcd.conf.example`` in the openstack-ansible repo
or adjust the example below to match your infrastructure hosts:

.. code-block:: yaml

  etcd_hosts:
    infra1:
      ip: 172.20.236.111
    infra2:
      ip: 172.20.236.112
    infra3:
      ip: 172.20.236.113

Copy the neutron environment overrides to
``/etc/openstack_deploy/env.d/neutron.yml`` to disable the creation of the
neutron agents container, and implement the calico-dhcp-agent hosts group
containing all compute hosts.

.. code-block:: yaml

  component_skel:
    neutron_calico_dhcp_agent:
      belongs_to:
      - neutron_all

  container_skel:
    neutron_agents_container:
      contains: {}
    neutron_calico_dhcp_agent_container:
      belongs_to:
        - compute_containers
      contains:
        - neutron_calico_dhcp_agent
      properties:
        is_metal: true
        service_name: neutron

Configure networking-calico Neutron Plugin
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the following in ``/etc/openstack_deploy/user_variables.yml``.

.. code-block:: yaml

  neutron_plugin_type: ml2.calico
  nova_network_type: calico

Installation
~~~~~~~~~~~~

After multi-node OpenStack cluster is configured as detailed above; start
the OpenStack deployment as listed in the OpenStack-Ansible Install guide by
running all playbooks in sequence on the deployment host
