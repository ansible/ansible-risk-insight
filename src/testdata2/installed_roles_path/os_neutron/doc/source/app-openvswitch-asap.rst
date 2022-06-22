============================================================
Scenario - Using Open vSwitch w/ ASAP :sup:`2` (Direct Mode)
============================================================

Overview
~~~~~~~~

With appropriate hardware, operators can choose to utilize
ASAP :sup:`2`-accelerated Open vSwitch instead of unaccelerated Open vSwitch
for the Neutron virtual network infrastructure. ASAP :sup:`2` technology
offloads packet processing onto hardware built into the NIC rather than using
the CPU of the host. It requires careful consideration and planning before
implementing. This document outlines how to set it up in your environment.

.. note::

  ASAP :sup:`2` is a proprietary feature provided with certain Mellanox NICs,
  including the ConnectX-5 and ConnectX-6. Future support is not
  guaranteed. This feature is considered *EXPERIMENTAL* and should not
  be used for production workloads. There is no guarantee of upgradability
  or backwards compatibility.

.. note::

  Hardware offloading is not yet compatible with the ``openvswitch`` firewall
  driver. To ensure flows are offloaded, port security must be disabled.
  Information on disabling port security is discussed later in this document.

Recommended reading
~~~~~~~~~~~~~~~~~~~

This guide is a variation of the standard Open vSwitch and SR-IOV deployment
guides available at:

* `<https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-openvswitch.html>`_

* `<https://docs.openstack.org/openstack-ansible-os_neutron/latest/configure-network-services.html#sr-iov-support-optional>`_

The following resources may also be helpful:

* `<https://docs.openstack.org/neutron/latest/admin/config-sriov.html>`_

* `<https://docs.openstack.org/neutron/latest/admin/config-ovs-offload.html>`_

* `<https://www.mellanox.com/related-docs/prod_software/ASAP2_Hardware_Offloading_for_vSwitches_User_Manual_v4.4.pdf>`_

* `<https://docs.nvidia.com/networking/pages/viewpage.action?pageId=61869597>`_

Prerequisites
~~~~~~~~~~~~~

To enable SR-IOV and PCI passthrough capabilities on a Linux platform,
ensure that VT-d/VT-x are enabled for Intel processors and AMD-V/AMD-Vi are
enabled for AMD processors. Such features are typically enabled in the BIOS.

On an Intel platform, the following kernel parameters are required and can be
added to the GRUB configuration:

.. code-block:: console

  GRUB_CMDLINE_LINUX="... iommu=pt intel_iommu=on"

On an AMD platform, use these parameters instead:

.. code-block:: console

  GRUB_CMDLINE_LINUX="... iommu=pt amd_iommu=on"

Update GRUB and reboot the host(s).

SR-IOV provides virtual functions (VFs) that can be presented to instances as
network interfaces and are used in lieu of tuntap interfaces. Configuration
of VFs is outside the scope of this guide. The following links may be helpful:

* `<https://community.mellanox.com/s/article/getting-started-with-mellanox-asap-2>`_

* `<https://community.mellanox.com/s/article/howto-configure-sr-iov-for-connectx-4-connectx-5-with-kvm--ethernet-x>`_

Deployment
~~~~~~~~~~

Configure your networking according the Open vSwitch implementation docs:

* `Scenario - Using Open vSwitch
  <https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-openvswitch.html>`_

.. note::

  At this time, only a single (non-bonded) interface is supported.

An example provider network configuration has been provided below:

.. code-block:: console

  - network:
      container_bridge: "br-provider"
      container_type: "veth"
      type: "vlan"
      range: "700:709"
      net_name: "physnet1"
      network_interface: "ens4f0"
      group_binds:
        - neutron_openvswitch_agent

Add a ``nova_pci_passthrough_whitelist`` entry to ``user_variables.yml``, where
``devname`` is the name of the interface connected to the provider bridge and
``physical_network`` is the name of the provider network.

.. code-block:: console

  nova_pci_passthrough_whitelist: '{"devname":"ens4f0","physical_network":"physnet1"}'

.. note::

  In the respective network block configured in ``openstack_user_config.yml``,
  ``devname`` corresponds to ``network_interface`` and ``physical_network``
  corresponds to ``net_name``.

To enable the ``openvswitch`` firewall driver rather than the default
``iptables_hybrid`` firewall driver, add the following overrides to
``user_variables.yml``:

.. code-block:: console

  neutron_ml2_conf_ini_overrides:
    securitygroup:
      firewall_driver: openvswitch
  neutron_openvswitch_agent_ini_overrides:
    securitygroup:
      firewall_driver: openvswitch

.. note::

  Hardware-offloaded flows are **not** activated for ports utilizing security
  groups or port security. Be sure to disable port security *and* security
  groups on individual ports or networks when hardware offloading is required.

Once the OpenStack cluster is configured, start the OpenStack deployment as
listed in the OpenStack-Ansible Install guide by running all playbooks in
sequence on the deployment host.

Post-Deployment
~~~~~~~~~~~~~~~

Once the deployment is complete, create the VFs that will be used for SR-IOV.
In this example, the physical function (PF) is ``ens4f0``. It will
simultaneously be connected to the Neutron provider bridge ``br-provider``.

1. On each compute node, determine the maximum number of VFs a PF can support:

.. code-block:: console

  # cat /sys/class/net/ens4f0/device/sriov_totalvfs

.. note::

  To adjust ``sriov_totalvfs`` please refer to Mellanox documentation.

2. On each compute node, create the VFs:

.. code-block:: console

  # echo '8' > /sys/class/net/ens4f0/device/sriov_numvfs

Configure Open vSwitch hardware offloading
------------------------------------------

1. Unbind the VFs from the Mellanox driver:

.. code-block:: console

  # for vf in `grep PCI_SLOT_NAME /sys/class/net/ens4f0/device/virtfn*/uevent | cut -d'=' -f2`
    do
      echo $vf > /sys/bus/pci/drivers/mlx5_core/unbind
    done

2. Enable the switch in the NIC:

.. code-block:: console

  # PCI_ADDR=`grep PCI_SLOT_NAME /sys/class/net/ens4f0/device/uevent | sed 's:.*PCI_SLOT_NAME=::'`
  # devlink dev eswitch set pci/$PCI_ADDR mode switchdev

3. Enable hardware offload filters with TC:

.. code-block:: console

  # ethtool -K ens4f0 hw-tc-offload on

4. Rebind the VFs to the Mellanox driver:

.. code-block:: console

  # for vf in `grep PCI_SLOT_NAME /sys/class/net/ens4f0/device/virtfn*/uevent | cut -d'=' -f2`
    do
      echo $vf > /sys/bus/pci/drivers/mlx5_core/bind
    done

5. Enable hardware offloading in OVS:

.. code-block:: console

  # ovs-vsctl set Open_vSwitch . other_config:hw-offload=true
  # ovs-vsctl set Open_vSwitch . other_config:max-idle=30000

6. Restart Open vSwitch

.. code-block:: console

  # systemctl restart openvswitch-switch

7. Restart the Open vSwitch agent

.. code-block:: console

  # systemctl restart neutron-openvswitch-agent

8. Restart the Nova compute service

.. code-block:: console

  # systemctl restart nova-compute

.. warning::

  Changes to ``sriov_numvfs`` as well as the built-in NIC switch will not
  persist a reboot and must be performed every time the server is started.

Verify operation
~~~~~~~~~~~~~~~~

To verify operation of hardware-offloaded Open vSwitch, you must create
a virtual machine instance using an image with the proper network drivers.

The following images are known to contain working drivers:

* `Ubuntu 18.04 LTS (Bionic) <https://cloud-images.ubuntu.com/bionic/current/bionic-server-cloudimg-amd64.img>`_

* `Ubuntu 20.04 LTS (Focal) <https://cloud-images.ubuntu.com/focal/current/focal-server-cloudimg-amd64.img>`_

* `Centos 8 Stream <https://cloud.centos.org/centos/8-stream/>`_

* `Centos 9 Stream <https://cloud.centos.org/centos/9-stream/>`_

Before creating an instance, a Neutron port must be created that has the
following characteristics:

:code:`--vnic-type direct --binding-profile '{"capabilities": ["switchdev"]}'`

To ensure flows are offloaded, disable port security with the
``--disable-port-security`` argument.

An example of the full command can be seen here:

.. code-block:: console

  # openstack port create \
    --network <network> \
    --vnic-type direct --binding-profile '{"capabilities": ["switchdev"]}' \
    --disable-port-security \
    <name>

The port can then be attached to the instance at boot. Once booted, the port
will be updated to reflect the PCI address of the corresponding virtual
function:

.. code-block:: console

  root@aio1-utility-container-8c0b0916:~# openstack port show -c binding_profile testport2
  +-----------------+------------------------------------------------------------------------------------------------------------------+
  | Field           | Value                                                                                                            |
  +-----------------+------------------------------------------------------------------------------------------------------------------+
  | binding_profile | capabilities='[u'switchdev']', pci_slot='0000:21:00.6', pci_vendor_info='15b3:1016', physical_network='physnet1' |
  +-----------------+------------------------------------------------------------------------------------------------------------------+

Observing traffic
-----------------

From the compute node, perform a packet capture on the representor port
that corresponds to the virtual function attached to the instance. In this
example, the interface is ``eth1``.

.. code-block:: console

  root@compute1:~# tcpdump -nnn -i eth1 icmp
  tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
  listening on eth1, link-type EN10MB (Ethernet), capture size 262144 bytes

Perform a ping from another host and observe the traffic at the representor
port:

.. code-block:: console

  root@infra2:~# ping 192.168.88.151 -c5
  PING 192.168.88.151 (192.168.88.151) 56(84) bytes of data.
  64 bytes from 192.168.88.151: icmp_seq=1 ttl=64 time=48.3 ms
  64 bytes from 192.168.88.151: icmp_seq=2 ttl=64 time=1.52 ms
  64 bytes from 192.168.88.151: icmp_seq=3 ttl=64 time=0.586 ms
  64 bytes from 192.168.88.151: icmp_seq=4 ttl=64 time=0.688 ms
  64 bytes from 192.168.88.151: icmp_seq=5 ttl=64 time=0.775 ms

  --- 192.168.88.151 ping statistics ---
  5 packets transmitted, 5 received, 0% packet loss, time 4045ms
  rtt min/avg/max/mdev = 0.586/10.381/48.335/18.979 ms

  root@compute1:~# tcpdump -nnn -i eth1 icmp
  tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
  listening on eth1, link-type EN10MB (Ethernet), capture size 262144 bytes
  19:51:09.684957 IP 192.168.88.254 > 192.168.88.151: ICMP echo request, id 11168, seq 1, length 64
  19:51:09.685448 IP 192.168.88.151 > 192.168.88.254: ICMP echo reply, id 11168, seq 1, length 64

When offloading is handled in the NIC, only the first packet(s) of the
flow will be visible in the packet capture.

The following command can be used to dump flows in the kernel datapath:

:code:`# ovs-appctl dpctl/dump-flows type=ovs`

The following command can be used to dump flows that are offloaded:

:code:`# ovs-appctl dpctl/dump-flows type=offloaded`
