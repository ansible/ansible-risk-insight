=================
Configuring Trove
=================

.. note::

   Care should be taken when deploying Trove in production environments.
   Be sure to fully understand the security implications of the deployed
   architecture.

Trove provides DBaaS to an OpenStack deployment. It deploys guest VMs
that provide the desired DB for use by the end consumer. The trove
guest VMs need connectivity back to the trove services via RPC
(oslo.messaging) and the OpenStack services. The way these guest VM
get access to those services could be via internal networking (in the
case of oslo.messaging) or via public interfaces (in the case of
OpenStack services). For the example configuration, we'll designate a
provider network as the network for trove to provision on each guest
VM. The guest can then connect to oslo.messaging via this network and to the
OpenStack services externally. Optionally, the guest VMs could use the internal
network to access OpenStack services, but that would require more containers
being bound to this network.

The deployment configuration outlined below may not be appropriate for
production environments. Review this very carefully with your own security
requirements.

Setup a neutron network for use by trove
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Trove needs connectivity between the control plane and the DB guest VMs. For
this purpose a provider network should be created which bridges the trove
containers (if the control plane is installed in a container) or hosts with
VMs. In a general case, neutron networking can be a simple flat network.
An example entry into ``openstack_user_config.yml`` is shown below:

.. code-block:: yaml

     - network:
        container_bridge: "br-dbaas"
        container_type: "veth"
        container_interface: "eth13"
        host_bind_override: "eth13"
        ip_from_q: "dbaas"
        type: "flat"
        net_name: "dbaas-mgmt"
        group_binds:
          - neutron_linuxbridge_agent
          - oslomsg_rpc
          - trove_all

Make sure to modify the other entries in this file as well.

The ``net_name`` will be the physical network that is specified when creating
the neutron network. The default value of ``dbaas-mgmt`` is also used to
lookup the addresses of the rpc messaging container. If the default is not used
then some variables in ``defaults\main.yml`` will need to be overwritten.

By default this role will not create the neutron network automaticaly. However,
the default values can be changed to create the neutron network. See the
``trove_service_net_*`` variable in ``defaults\main.yml``. By customizing the
``trove_service_net_*`` variables and having this role create the neutron
network a full deployment of the OpenStack and DBaaS can proceed
without interruption or intervention.

The following is an example how to set up a provider network in neutron
manually, if so desired:

.. code-block:: bash

    neutron net-create dbaas_service_net --shared \
                                    --provider:network_type flat \
                                    --provider:physical_network dbaas-mgmt

    neutron subnet-create dbaas_service_net 172.29.252.0/22 --name dbaas_service_subnet
                          --ip-version=4 \
                          --allocation-pool start=172.29.252.110,end=172.29.255.255 \
                          --enable-dhcp \
                          --dns-nameservers list=true 8.8.4.4 8.8.8.8

Special attention needs to be applied to the ``--allocation-pool`` to not have
ips which overlap with ips assigned to hosts or containers (see the ``used_ips``
variable in ``openstack_user_config.yml``)

.. note::
    This role needs the neutron network created before it can run properly
    since the trove guest agent configuration file contains that information.


Building Trove images
~~~~~~~~~~~~~~~~~~~~~

When building disk image for the guest VM deployments there are many items
to consider. Listed below are a few:

#. Security of the VM and the network infrastructure
#. What DBs will be installed
#. What DB services will be supported
#. How will the images be maintained

Images can be built using the ``diskimage-builder`` tooling. The trove
virtual environment can be tar'd up from the trove containers and deployed to
the images using custom ``diskimage-builder`` elements.

See the ``trove/integration/scripts/files/elements`` directory contents in
the OpenStack Trove project for ``diskimage-builder`` elements to build trove
disk images.


Use stand-alone RabbitMQ
~~~~~~~~~~~~~~~~~~~~~~~~

Since Trove uses RabbitMQ to interact with guest servers it requires you to
pass the neutron network into the RabbitMQ container which is a security risk.
As a result, you might want to isolate Trove from other services in terms of
the RabbitMQ cluster and use a standalone one.

In order to deploy new RabbitMQ cluster and use it for Trove, you will need
to:

#. Create a new group for RabbitMQ containers. You will need to create a file
   inside ``/etc/openstack_depoy/env.d`` which defines group mappings

    .. code-block:: yaml

        component_skel:
          trove_rabbitmq:
            belongs_to:
              - trove_mq_all

        container_skel:
          trove_rabbit_container:
            belongs_to:
              - trove-mq_containers
            contains:
              - trove_rabbitmq

        physical_skel:
          trove-mq_containers:
            belongs_to:
              - all_containers
          trove-mq_hosts:
            belongs_to:
              - hosts

#. Define on which hosts this group will be deployed. This can be done either
   with a new file in conf.d or inside openstack_user_config.yml

    .. code-block:: yaml

        trove-mq_hosts:
          aio1:
            ip: 172.29.236.100

#. Add to the dbaas network mapping for the new group:

.. code-block:: yaml

     - network:
        container_bridge: "br-dbaas"
        container_type: "veth"
        container_interface: "eth14"
        host_bind_override: "eth14"
        ip_from_q: "dbaas"
        type: "flat"
        net_name: "dbaas-mgmt"
        group_binds:
          - neutron_linuxbridge_agent
          - oslomsg_rpc
          - trove_rabbitmq

#. Create overrides for dedicated rabbitmq containers, ie
   ``/etc/openstack_deploy/group_vars/trove_rabbitmq.yml``

    .. code-block:: yaml

        rabbitmq_cluster_name: trove
        rabbitmq_cookie_token: <token>
        rabbitmq_monitoring_password: <password>

#. Create overrides for trove service contaienrs, ie
   ``/etc/openstack_deploy/group_vars/trove_all.yml``

    .. note::

        For notifications we still want to use main RabbitMQ cluster

    .. code-block:: yaml

        oslomsg_rpc_host_group: trove_rabbitmq
        oslomsg_rpc_servers: "{{ groups[oslomsg_rpc_host_group] | map('extract', hostvars, 'ansible_host') | list | join(',') }}"
        trove_guest_oslomsg_notify_servers: "{{ rabbitmq_servers }}"

#. Run playbooks to create rabbitmq containers and deploy cluster on them

    .. code-block:: bash

        openstack-ansible playbooks/lxc-containers-create.yml --limit trove_rabbitmq,lxc_hosts
        openstack-ansible playbooks/rabbitmq-install.yml -e rabbitmq_host_group=trove_rabbitmq
