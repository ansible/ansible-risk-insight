========================================
Scenario - OpenDaylight and Open vSwitch
========================================

Overview
~~~~~~~~

Deployers can choose to enhance neutron capabilities by means of the
OpenDaylight SDN Controller, which works together with Open vSwitch to provide
advanced networking capabilities. This document explains how to use them
in your environment.

Recommended reading
~~~~~~~~~~~~~~~~~~~

Since this is an extension of the basic Open vSwitch scenario, it is worth
reading that scenario to get some background. It is also recommended to be
familiar with OpenDaylight and networking-odl projects and their configuration.

* `Scenario: Open vSwitch <app-openvswitch.html>`_
* `OpenDaylight SDN Controller <https://docs.opendaylight.org/en/latest/>`_
* `Networking-odl <https://github.com/openstack/networking-odl>`_

Prerequisites
~~~~~~~~~~~~~

The `OpenDaylight Ansible role <https://wiki.opendaylight.org/view/Deployment#Ansible_Role>`_
needs to be available in Ansible's role path.

OpenStack-Ansible user variables
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Set the following user variables in your
``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

  ### Ensure the openvswitch kernel module is loaded
  openstack_host_specific_kernel_modules:
    - name: "openvswitch"
      pattern: "CONFIG_OPENVSWITCH"
      group: "network_hosts"

  ### Use OpenDaylight SDN Controller
  neutron_plugin_type: "ml2.opendaylight"
  odl_ip: "{{ hostvars[groups['opendaylight'][0]]['ansible_facts']['default_ipv4']['address'] }}"
  neutron_opendaylight_conf_ini_overrides:
    ml2_odl:
      url: "http://{{ odl_ip }}:8180/controller/nb/v2/neutron"
      username: <username>
      password: <password>

Most of the content of this file is self-explanatory. The first block is used
to deploy Open vSwitch in all network hosts.

The second block is instructing Ansible to deploy OpenDaylight SDN Controller.
This is done by specifying ``neutron_plugin_type`` to ``ml2.opendaylight``.
The IP address of the OpenDaylight controller needs to be inferred from the
deployment configuration as well. That can be used with a line such as the one
in the example.

After that, some configuration is needed to integrate OpenDaylight and Neutron,
using the ``ml2_odl`` section.

* **url**: OpenDaylight's northbound url. This is automatically retrieved from
  the deployment configuration, so just need to copy the example line.
* **username**: OpenDaylight northbound API username
* **password**: OpenDaylight northbound API password for <username>

Apart from these options, the deployer might want to change the installation
method for OpenDaylight Ansible role. This role uses pre-packaged binaries,
which can be either ``deb`` or ``rpm`` files, and by default it will download
these binaries from OpenDaylight repositories, trying to guess the correct
package depending on the underlying operating system.

Also, the set of features that will be enabled in the OpenDaylight SDN
controller defaults to ``odl-netvirt-openstack``, which is the minimum for an
OpenStack integration. The deployer can modify this value by providing a list
of feature names in the ``opendaylight_extra_features`` variable.

For more information, see OpenDaylight Ansible role documentation.

L3 configuration
~~~~~~~~~~~~~~~~

L3 services are by default provided by the neutron-l3-agent. ODL is capable of
providing L3 services too and if ODL is deployed, it is actually recommended to
use them instead of neutron. Remember that L3 services allow, among other
things, to give VMs connectivity to the internet.

To activate the ODL L3 services, you should add to the above explained
variables:

.. code-block:: yaml

 # Activate the L3 capabilities of ODL
 neutron_plugin_base:
  - odl-router_v2
  - metering

If you want to use the L3 capabilities, you will need to define a external
Neutron network and set a gateway. Note that the br-vlan interface of the nodes
could be a perfect interface for that gateway, although it depends on your
network topology.

SFC configuration
~~~~~~~~~~~~~~~~~

It is possible to have an openstack-ansible deployment with SFC capabilities.
The following config needs to be added to the above described
``/etc/openstack_deploy/user_variables.yml`` :

.. code-block:: yaml

 neutron_plugin_base:
  - router
  - metering
  - flow_classifier
  - sfc

When using this configuration, networking-sfc will be deployed and SFC features
will be activated in ODL. A SFC topology could be then set up through the
networking-sfc API or through an orchestrator like tacker (if deployed).


BGPVPN configuration
~~~~~~~~~~~~~~~~~~~~

ODL provides support for extending L3 services over DC-GW by BGPVPN. This way
Openstack configures ODL as BGP speaker to exchange the routes with DC-GW to
establish the communication between Tenant VMs and external world in the
data path.

To activate BGPVPN service, you should add the following variables in addition
to the OpenStack-Ansible user variables mentioned above.

.. code-block:: yaml

 # Activate the BGPVPN capabilities of ODL
 neutron_plugin_base:
  - odl-router_v2
  - bgpvpn


Security information
~~~~~~~~~~~~~~~~~~~~

Communications between the OpenDaylight SDN Controller and Open vSwitch are not
secured by default. For further information on securing this interface, see
these manuals:

* `TLS Support on OpenDaylight OpenFlow plugin
  <https://wiki.opendaylight.org/view/OpenDaylight_OpenFlow_Plugin:_TLS_Support>`__.

* `Secure Communication Between OpenFlow Switches and Controllers
  <https://www.thinkmind.org/download.php?articleid=afin_2015_2_30_40047>`__.
