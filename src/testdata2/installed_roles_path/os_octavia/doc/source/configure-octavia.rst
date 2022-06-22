=========================================================
Configuring the Octavia Load Balancing service (optional)
=========================================================

Octavia is an OpenStack project which provides operator-grade Load Balancing
(as opposed to the namespace driver) by deploying each individual load
balancer to its own virtual machine and leveraging haproxy to perform the
load balancing.

Octavia is scalable and has built-in high availability through active-passive.

OpenStack-Ansible deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

#. Create ``br-lbaas`` bridge on the controllers. Creating br-lbaas is done during
   the deployers host preparation and is out of scope of openstack-ansible.
   Some explanation of how br-lbaas is used is given below.
#. Create the openstack-ansible container(s) for Octavia. To do that you need
   to define hosts for ``octavia-infra_hosts`` group in
   ``openstack_user_config.yml``. Once you do this, run the following playbook:

   .. code-block:: yaml

      openstack-ansible playbooks/containers-lxc-create.yml --limit lxc_hosts,octavia_all

#. Define required overrides of the variables in defaults/main.yml of the
   openstack-ansible octavia role.
#. Run the os-octavia playbook

   .. code-block:: yaml

      openstack-ansible playbooks/os-octavia-install.yml

#. Run the haproxy-install.yml playbook to add the new octavia API endpoints
   to the load balancer.

Setup a neutron network for use by octavia
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Octavia needs connectivity between the control plane and the
load balancing VMs. For this purpose a provider network should be
created which gives L2 connectivity between the octavia services
on the controllers (either containerised or deployed on metal)
and the octavia amphora VMs. Refer to the appropriate documentation
for the octavia service and consult the tests in this project
for a working example.

Special attention needs to be applied to the provider network
``--allocation-pool`` not to have ip addresses which overlap with
those assigned to hosts, lxc containers or other infrastructure such
as routers or firewalls which may be in use.

An example which gives 172.29.232.0-9/22 to the OSA dynamic inventory
and the remainder of the addresses to the neutron allocation pool
without overlap is as follows:

In ``openstack_user_config.yml`` the following:

.. code-block:: yaml

   #the address range for the whole lbaas network
   cidr_networks:
      lbaas: 172.29.232.0/22

   #the range of ip addresses excluded from the dynamic inventory
   used_ips:
      - "172.29.232.10,172.29.235.200"

And define in ``user_variables.yml``:

.. code-block:: yaml

   #the range of addresses which neutron can allocate for amphora VM
   octavia_management_net_subnet_allocation_pools: "172.29.232.10-172.29.235.200"

.. note::
    The system will deploy an iptables firewall if ``octavia_ip_tables_fw`` is set
    to ``True`` (the default). This adds additional protection to the control plane
    in the rare instance a load balancing vm is compromised. Please review carefully
    the rules and adjust them for your installation. Please be aware that logging
    of dropped packages is not enabled and you will need to add those rules manually.

FLAT networking scenario
------------------------

In a general case, neutron networking can be a simple flat network. However in
a complex case, this can be whatever you need and want. Ensure you adjust the
deployment accordingly. An example entry into ``openstack_user_config.yml`` is
shown below:

.. code-block:: yaml

     - network:
        container_bridge: "br-lbaas"
        container_type: "veth"
        container_interface: "eth14"
        host_bind_override: "bond0"  # Defines neutron physical network mapping
        ip_from_q: "octavia"
        type: "flat"
        net_name: "octavia"
        group_binds:
          - neutron_linuxbridge_agent
          - octavia-worker
          - octavia-housekeeping
          - octavia-health-manager


There are a couple of variables which need to be adjusted if you don't use
``lbaas`` for the provider network name and ``lbaas-mgmt`` for the neutron
name. Furthermore, the system tries to infer certain values based on the
inventory which might not always work and hence might need to be explicitly
declared. Review the file ``defaults/main.yml`` for more information.

The octavia ansible role can create the required neutron networks itself.
Please review the corresponding settings - especially
``octavia_management_net_subnet_cidr`` should be adjusted to suit your
environment. Alternatively, the neutron network  can be pre-created elsewhere
and consumed by Octavia.


VLAN networking scenario
------------------------

In case you want to leverage standard vlan networking for the Octavia
management network the definition in ``openstack_user_config.yml`` may
look like this:

.. code-block:: yaml

    - network:
        container_bridge: "br-lbaas"
        container_type: "veth"
        container_interface: "eth14"
        ip_from_q: "lbaas"
        type: "raw"
        net_name: lbaas
        group_binds:
          - neutron_linuxbridge_agent
          - octavia-worker
          - octavia-housekeeping
          - octavia-health-manager

Add extend ``user_variables.yml`` with following overrides:

.. code-block:: yaml

   octavia_provider_network_name: vlan
   octavia_provider_network_type: vlan
   octavia_provider_segmentation_id: 400
   octavia_provider_inventory_net_name: lbaas

In addition to this, you will need to ensure that you have an interface that
links neutron-managed br-vlan with br-lbaas on the controller nodes (for the case
when br-vlan already exists on the controllers when they also host the neutron
L3 agent). Making veth pairs or macvlans for this might be suitable.

Building Octavia images
~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    The default behavior is to download a test image from the OpenStack artifact
    storage the Octavia team provides daily. Because this image doesn't apply
    operating system security patches in a timely manner it is unsuited
    for production use.

    Some Operating System vendors might provide official amphora builds or an
    organization might maintain their own artifact storage - for those cases the
    automatic download can be leveraged, too.

Images using the ``diskimage-builder`` must be built outside of a container.
For this process, use one of the physical hosts within the environment.

#. Install the necessary packages and configure a Python virtual environment

   .. code-block:: bash

      apt-get install qemu uuid-runtime curl kpartx git jq python3-pip
      pip3 install virtualenv

      virtualenv -p /usr/bin/python3 /opt/octavia-image-build
      source /opt/octavia-image-build/bin/activate

#. Clone the necessary repositories and dependencies

   .. code-block:: bash

     git clone https://opendev.org/openstack/octavia.git

     /opt/octavia-image-build/bin/pip install --isolated \
       git+https://git.openstack.org/openstack/diskimage-builder.git

#. Run Octavia's diskimage script

   In the ``octavia/diskimage-create`` directory run:

   .. code-block:: bash

     ./diskimage-create.sh

   Disable ``octavia-image-build`` venv:

   .. code-block:: bash

      deactivate


#. Upload the created user images into the Image (glance) Service:

   .. code-block:: bash

      openstack image create --disk-format qcow2 \
         --container-format bare --tag octavia-amphora-image --file amphora-x64-haproxy.qcow2 \
         --private --project service amphora-x64-haproxy

   .. note::
        Alternatively you can specify the new image in the appropriate settings and rerun the
        ansible with an appropriate tag.

You can find more information about the diskimage script and the process at
https://opendev.org/openstack/octavia/tree/master/diskimage-create

Here is a script to perform all those tasks at once:

   .. code-block:: bash

          #/bin/sh

          apt-get install qemu uuid-runtime curl kpartx git jq
          pip -v >/dev/null || {apt-get install python3-pip}
          pip3 install virtualenv
          virtualenv -p /usr/bin/python3 /opt/octavia-image-build || exit 1
          source /opt/octavia-image-build/bin/activate

          pushd /tmp
          git clone https://opendev.org/openstack/octavia.git
          /opt/octavia-image-build/bin/pip install --isolated \
           git+https://git.openstack.org/openstack/diskimage-builder.git

          pushd octavia/diskimage-create
          ./diskimage-create.sh
          mv amphora-x64-haproxy.qcow2 /tmp
          deactivate

          popd
          popd

          # upload image
          openstack image delete amphora-x64-haproxy
          openstack image create --disk-format qcow2 \
            --container-format bare --tag octavia-amphora-image --file /tmp/amphora-x64-haproxy.qcow2 \
            --private --project service amphora-x64-haproxy

.. note::
    If you have trouble installing dib-utils from pipy consider
    installing it directly from source
    `pip install git+https://opendev.org/openstack/dib-utils.git`

Creating the cryptographic certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. note::
    For production installation make sure that you review this very
    carefully with your own security requirements and potentially use
    your own CA to sign the certificates.

The system will automatically generate and use self-signed
certificates with different Certificate Authorities for control plane
and amphora. Make sure to store a copy in a safe place for potential
disaster recovery.

Optional: Configuring Octavia with ssh access to the amphora
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In rare cases it might be beneficial to gain ssh access to the
amphora for additional trouble shooting. Follow these steps to
enable access.

#. Configure Octavia accordingly

   Add a ``octavia_ssh_enabled: True`` to the user file in
   /etc/openstack-deploy

#. Run ``os_octavia`` role. SSH key will be generated and uploaded

.. note::
    SSH key will be stored on the ``octavia_keypair_setup_host`` (which
    by default is ``localhost``) in ``~/.ssh/{{ octavia_ssh_key_name }}``

Optional: Tuning Octavia for production use
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Please have a close look at the ``main.yml`` for tunable parameters.
The most important change is to set Octavia into ACTIVE_STANDBY mode
by adding ``octavia_loadbalancer_topology: ACTIVE_STANDBY`` and
``octavia_enable_anti_affinity=True`` to ensure that the active and passive
amphora are (depending on the anti-affinity filter deployed in nova)  on two
different hosts to the user file in /etc/openstack-deploy

Also we suggest setting more specific ``octavia_cert_dir`` to prevent
accidental certificate rotation.
