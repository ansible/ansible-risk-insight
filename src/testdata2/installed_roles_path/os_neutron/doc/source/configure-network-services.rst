=======================================================
Configuring the Networking service (neutron) (optional)
=======================================================

The OpenStack Networking service (neutron) includes the following services:

Firewall as a Service (FWaaS)
  Provides a software-based firewall that filters traffic from the router.

VPN as a Service (VPNaaS)
  Provides a method for extending a private network across a public network.

BGP Dynamic Routing service
  Provides a means for advertising self-service (private) network prefixes
  to physical network devices that support BGP.

SR-IOV Support
  Provides the ability to provision virtual or physical functions to guest
  instances using SR-IOV and PCI passthrough. (Requires compatible NICs)


Firewall service (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following procedure describes how to modify the
``/etc/openstack_deploy/user_variables.yml`` file to enable FWaaS.

Deploying FWaaS v1
------------------

.. note::

  The FWaaS v1 API is deprecated upstream. While FWaaS v1.0 is still
  maintained, new features will be implemented in FWaaS v2.0 API.

#. Override the default list of neutron plugins to include
   ``firewall``:

   .. code-block:: yaml

      neutron_plugin_base:
        - firewall
        - ...

#. ``neutron_plugin_base`` is as follows:

   .. code-block:: yaml

      neutron_plugin_base:
         - router
         - firewall
         - vpnaas
         - metering
         - qos

#. Execute the neutron install playbook in order to update the configuration:

   .. code-block:: shell-session

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-neutron-install.yml

#. Execute the horizon install playbook to show the FWaaS panels:

   .. code-block:: shell-session

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-horizon-install.yml

The FWaaS default configuration options may be changed through the
`conf override`_ mechanism using the ``neutron_neutron_conf_overrides``
dict.

Deploying FWaaS v2
------------------

FWaaS v2 is the next generation Neutron firewall service and will provide
a rich set of APIs for securing OpenStack networks. It is still under
active development.

Refer to the `FWaaS 2.0 API specification
<https://specs.openstack.org/openstack/neutron-specs/specs/newton/fwaas-api-2.0.html>`_
for more information on these FWaaS v2 features.

FWaaS v2 requires the use of Open vSwitch. To deploy an environment using
Open vSwitch for virtual networking, please refer to the following
documentation:

* `Scenario - Using Open vSwitch <app-openvswitch.html>`_

* `Scenario - Using Open vSwitch with DVR
  <app-openvswitch-dvr.html>`_

Follow the steps below to deploy FWaaS v2:

.. note::
    FWaaS v1 and v2 cannot be deployed simultaneously.

#. Add the FWaaS v2 plugin to the ``neutron_plugin_base`` variable
   in ``/etc/openstack_deploy/user_variables.yml``:

   .. code-block:: yaml

      neutron_plugin_base:
        - router
        - metering
        - firewall_v2

   Ensure that ``neutron_plugin_base`` includes all of the plugins that you
   want to deploy with neutron in addition to the firewall_v2 plugin.

#. Run the neutron playbook to deploy the FWaaS v2 service plugin

   .. code-block:: console

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-neutron-install.yml


Virtual private network service - VPNaaS (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following procedure describes how to modify the
``/etc/openstack_deploy/user_variables.yml`` file to enable VPNaaS.

#. Override the default list of neutron plugins to include
   ``vpnaas``:

   .. code-block:: yaml

      neutron_plugin_base:
        - router
        - metering

#. ``neutron_plugin_base`` is as follows:

   .. code-block:: yaml

      neutron_plugin_base:
         - router
         - metering
         - vpnaas

#. Override the default list of specific kernel modules
   in order to include the necessary modules to run ipsec:

   .. code-block:: yaml

      openstack_host_specific_kernel_modules:
         - { name: "ebtables", pattern: "CONFIG_BRIDGE_NF_EBTABLES=", group: "network_hosts" }
         - { name: "af_key", pattern: "CONFIG_NET_KEY=", group: "network_hosts" }
         - { name: "ah4", pattern: "CONFIG_INET_AH=", group: "network_hosts" }
         - { name: "ipcomp", pattern: "CONFIG_INET_IPCOMP=", group: "network_hosts" }

#. Execute the openstack hosts setup in order to load the kernel modules at
   boot and runtime in the network hosts

   .. code-block:: shell-session

      # openstack-ansible openstack-hosts-setup.yml --limit network_hosts\
      --tags "openstack_hosts-config"

#. Execute the neutron install playbook in order to update the configuration:

   .. code-block:: shell-session

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-neutron-install.yml

#. Execute the horizon install playbook to show the VPNaaS panels:

   .. code-block:: shell-session

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-horizon-install.yml

The VPNaaS default configuration options are changed through the
`conf override`_ mechanism using the ``neutron_neutron_conf_overrides``
dict.

.. _conf override: https://docs.openstack.org/openstack-ansible/latest/admin/openstack-operations.html

You can also define customized configuration files for VPN service with the variable
``neutron_vpnaas_custom_config``:

.. code-block:: yaml

   neutron_vpnaas_custom_config:
      - src: "/etc/openstack_deploy/strongswan/strongswan.conf.template"
        dest: "{{ neutron_conf_dir }}/strongswan.conf.template"
        condition: "{{ ansible_facts['os_family'] | lower == 'debian' }}"
      - src: "/etc/openstack_deploy/strongswan/strongswan.d"
        dest: "/etc/strongswan.d"
        condition: "{{ ansible_facts['os_family'] | lower == 'debian' }}"
      - src: "/etc/openstack_deploy/{{ neutron_vpnaas_distro_packages }}/ipsec.conf.template"
        dest: "{{ neutron_conf_dir }}/ipsec.conf.template"
      - src: "/etc/openstack_deploy/{{ neutron_vpnaas_distro_packages }}/ipsec.secret.template"
        dest: "{{ neutron_conf_dir }}/ipsec.secret.template"

With that ``neutron_l3_agent_ini_overrides`` should be also defined in 'user_variables.yml'
to tell ``l3_agent`` use the new config file:

.. code-block:: yaml

   neutron_l3_agent_ini_overrides:
         ipsec:
            enable_detailed_logging: True
         strongswan:
            strongswan_config_template : "{{ neutron_conf_dir }}/strongswan.conf.template"
         openswan:
            ipsec_config_template:  "{{ neutron_conf_dir }}/ipsec.conf.template"


BGP Dynamic Routing service (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The `BGP Dynamic Routing`_ plugin for neutron provides BGP speakers which can
advertise OpenStack project network prefixes to external network devices, such
as routers. This is especially useful when coupled with the `subnet pools`_
feature, which enables neutron to be configured in such a way as to allow users
to create self-service `segmented IPv6 subnets`_.

.. _BGP Dynamic Routing: https://docs.openstack.org/neutron/latest/admin/config-bgp-dynamic-routing.html
.. _subnet pools: https://docs.openstack.org/neutron/latest/admin/config-subnet-pools.html
.. _segmented IPv6 subnets: https://cloudbau.github.io/openstack/neutron/networking/2016/05/17/neutron-ipv6.html

The following procedure describes how to modify the
``/etc/openstack_deploy/user_variables.yml`` file to enable the BGP Dynamic
Routing plugin.

#. Add the BGP plugin to the ``neutron_plugin_base`` variable
   in ``/etc/openstack_deploy/user_variables.yml``:

   .. code-block:: yaml

      neutron_plugin_base:
        - ...
        - neutron_dynamic_routing.services.bgp.bgp_plugin.BgpPlugin

   Ensure that ``neutron_plugin_base`` includes all of the plugins that you
   want to deploy with neutron in addition to the BGP plugin.

#. Execute the neutron install playbook in order to update the configuration:

   .. code-block:: shell-session

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-neutron-install.yml


SR-IOV Support (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following procedure describes how to modify the OpenStack-Ansible
configuration to enable Neutron SR-IOV support.

.. _SR-IOV-Passthrough-For-Networking: https://wiki.openstack.org/wiki/SR-IOV-Passthrough-For-Networking


#. Define SR-IOV capable physical host interface for a provider network

   As part of every Openstack-Ansible installation, all provider networks
   known to Neutron need to be configured inside the
   ``/etc/openstack_deploy/openstack_user_config.yml`` file.
   For each supported network type (e.g. vlan), the attribute
   ``sriov_host_interfaces`` can be defined to map ML2 network names
   (``net_name`` attribute) to one or many physical interfaces.
   Additionally, the network will need to be assigned to the
   ``neutron_sriov_nic_agent`` container group.

   Example configuration:

   .. code-block:: yaml

      provider_networks
        - network:
          container_bridge: "br-vlan"
          container_type: "veth"
          container_interface: "eth11"
          type: "vlan"
          range: "1000:2000"
          net_name: "physnet1"
          sriov_host_interfaces: "p1p1,p4p1"
          group_binds:
            - neutron_linuxbridge_agent
            - neutron_sriov_nic_agent

#. Configure Nova

   With SR-IOV, Nova uses PCI passthrough to allocate VFs and PFs to guest
   instances. Virtual Functions (VFs) represent a slice of a physical NIC,
   and are passed as virtual NICs to guest instances. Physical Functions
   (PFs), on the other hand, represent an entire physical interface and are
   passed through to a single guest.

   To use PCI passthrough in Nova, the ``PciPassthroughFilter`` filter
   needs to be added to the `conf override`_
   ``nova_scheduler_default_filters``.
   Finally, PCI devices available for passthrough need to be allow via
   the `conf override`_
   ``nova_pci_passthrough_whitelist``.

   Possible options which can be configured:

   .. code-block:: yaml

      # Single device configuration
      nova_pci_passthrough_whitelist: '{ "physical_network":"physnet1", "devname":"p1p1" }'

      # Multi device configuration
      nova_pci_passthrough_whitelist: '[{"physical_network":"physnet1", "devname":"p1p1"}, {"physical_network":"physnet1", "devname":"p4p1"}]'

      # Whitelisting by PCI Device Location
      # The example pattern for the bus location '0000:04:*.*' is very wide. Make sure that
      # no other, unintended devices, are whitelisted (see lspci -nn)
      nova_pci_passthrough_whitelist: '{"address":"0000:04:*.*", "physical_network":"physnet1"}'

      # Whitelisting by PCI Device Vendor
      # The example pattern limits matches to PCI cards with vendor id 8086 (Intel) and
      # product id 10ed (82599 Virtual Function)
      nova_pci_passthrough_whitelist: '{"vendor_id":"8086", "product_id":"10ed", "physical_network":"physnet1"}'

      # Additionally, devices can be matched by their type, VF or PF, using the dev_type parameter
      # and type-VF or type-PF options
      nova_pci_passthrough_whitelist: '{"vendor_id":"8086", "product_id":"10ed", "dev_type":"type-VF", physical_network":"physnet1"}'

   It is recommended to use whitelisting by either the Linux device name
   (devname attribute) or by the PCI vendor and product id combination
   (``vendor_id`` and ``product_id`` attributes)

#. Enable the SR-IOV ML2 plugin

   The `conf override`_ ``neutron_plugin_type`` variable defines the core
   ML2 plugin, and only one plugin can be defined at any given time.
   The `conf override`_ ``neutron_plugin_types`` variable can contain a list
   of additional ML2 plugins to load. Make sure that only compatible
   ML2 plugins are loaded at all times.
   The SR-IOV ML2 plugin is known to work with the linuxbridge (``ml2.lxb``)
   and openvswitch (``ml2.ovs``) ML2 plugins.
   ``ml2.lxb`` is the standard activated core ML2 plugin.

   .. code-block:: yaml

      neutron_plugin_types:
        - ml2.sriov


#. Execute the Neutron install playbook in order to update the configuration:

   .. code-block:: shell-session

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-neutron-install.yml
       # openstack-ansible os-nova-install.yml


#. Check Neutron SR-IOV agent state

   After the playbooks have finished configuring Neutron and Nova, the new
   Neutron Agent state can be verified with:

   .. code-block:: shell-session

       # neutron agent-list --agent_type 'NIC Switch agent'
       +--------------------------------------+------------------+-----------+-------+----------------+-------------------------+
       | id                                   | agent_type       | host      | alive | admin_state_up | binary                  |
       +--------------------------------------+------------------+-----------+-------+----------------+-------------------------+
       | 3012ff0e-de35-447b-aff6-fdb55b04c518 | NIC Switch agent | compute01 | :-)   | True           | neutron-sriov-nic-agent |
       | bb0c0385-394d-4e72-8bfe-26fd020df639 | NIC Switch agent | compute02 | :-)   | True           | neutron-sriov-nic-agent |
       +--------------------------------------+------------------+-----------+-------+----------------+-------------------------+


Deployers can make changes to the SR-IOV nic agent default configuration
options via the ``neutron_sriov_nic_agent_ini_overrides`` dict.
Review the documentation on the `conf override`_ mechanism for more details.

