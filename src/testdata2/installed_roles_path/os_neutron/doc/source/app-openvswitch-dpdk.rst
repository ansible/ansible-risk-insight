=====================================
Scenario - Using Open vSwitch w/ DPDK
=====================================

Overview
~~~~~~~~

Operators can choose to utilize DPDK-accelerated Open vSwitch instead of
unaccelerated Open vSwitch or Linux Bridges for the Neutron virtual network
infrastructure. This architecture is best suited for NFV workloads and
requires careful consideration and planning before implementing. This
document outlines how to set it up in your environment.

.. warning::

  The current implementation of DPDK in OpenStack-Ansible is
  experimental and not production ready. There is no guarantee of
  upgradability or backwards compatibility between releases.

Recommended reading
~~~~~~~~~~~~~~~~~~~

We recommend that you read the following documents before proceeding:

* Neutron with Open vSwitch Scenario:
  `<https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-openvswitch.html>`_
* Open vSwitch with DPDK datapath:
  `<https://docs.openstack.org/neutron/latest/admin/config-ovs-dpdk.html>`_
* Getting the best performance from DPDK:
  `<https://doc.dpdk.org/guides/linux_gsg/nic_perf_intel_platform.html>`_
* OpenStack documentation on hugepages:
  `<https://docs.openstack.org/nova/latest/admin/huge-pages.html>`_

Prerequisites
~~~~~~~~~~~~~

To enable DPDK on a Linux platform, ensure that VT-d/VT-x are enabled for
Intel processors and AMD-V/AMD-Vi are enabled for AMD processors. Such
features are typically enabled in the BIOS.

On an Intel platform, the following kernel parameters are required and can be
added to the GRUB configuration:

.. code-block:: console

  GRUB_CMDLINE_LINUX="... iommu=pt intel_iommu=on"

On an AMD platform, use these parameters instead:

.. code-block:: console

  GRUB_CMDLINE_LINUX="... iommu=pt amd_iommu=on"

Update GRUB and reboot the host(s).

Hugepages are required for DPDK. Instances leveraging DPDK-accelerated
Open vSwitch must be configured to use hugepages by way of flavor
attributes. Those attributes and the configuration of hugepages are
described in this guide.

CPU frequency should be set to maximum for optimal performance. Many
hardware vendors set the energy saving properties in the BIOS that
may need to be modified. Changing the CPU frequency using ``cpufreq``
or similar utilities to ``performance`` from ``ondemand`` is recommended.

.. note::

  The playbooks currently only support a single NIC interface for DPDK. Multiple
  ports per NIC are not yet supported but may be at a later time. This guide
  assumes the NIC is bound to NUMA node0, but the instructions can be modified
  for NICs bound to other NUMA nodes..

NUMA topology
~~~~~~~~~~~~~

Non-uniform memory access (NUMA) is a computer memory design used in
multiprocessing. This guide cannot go into great depths about NUMA
architecture. However, there are some configurations to be made that
rely on the operator understanding NUMA characteristics of compute
nodes hosting workloads using DPDK-accelerated Open vSwitch.

To view the NUMA topology of a particular system, use the ``numactl``
command shown here:

.. code-block:: console

  root@compute1:~# numactl --hardware
  available: 2 nodes (0-1)
  node 0 cpus: 0 1 2 3 4 5 6 7 16 17 18 19 20 21 22 23
  node 0 size: 48329 MB
  node 0 free: 31798 MB
  node 1 cpus: 8 9 10 11 12 13 14 15 24 25 26 27 28 29 30 31
  node 1 size: 48379 MB
  node 1 free: 25995 MB
  node distances:
  node   0   1
    0:  10  20
    1:  20  10

The NUMA topology presented here corresponds to a host with 2x Intel Xeon 2450L
processors with 96 GB of total RAM. The RAM is evenly split between the two NUMA
nodes. Each CPU has 8 cores. With hyperthreading enabled, there are 16 threads
per CPU for a total of 32 threads or cores presented to the operating system.
It just so happens that this two-socket system has one NUMA node per socket,
however, that will not always be the case. Consult your system's documentation
for information unique to your system.

The first eight cores/cpus in the list for a given NUMA node can be considered
physical cores in the CPU. For NUMA node0, this would be cores 0-7. The other
eight cores, 16-23, are considered virtual sibling cores and are presented when
hyperthreading is enabled. The physical-to-virtual mapping can be determined
with the following commands:

.. code-block:: console

  root@compute1:~# for cpu in {0..7}; do cat /sys/devices/system/cpu/"cpu"$cpu/topology/thread_siblings_list; done
  0,16
  1,17
  2,18
  3,19
  4,20
  5,21
  6,22
  7,23

  root@compute1:~# for cpu in {8..15}; do cat /sys/devices/system/cpu/"cpu"$cpu/topology/thread_siblings_list; done
  8,24
  9,25
  10,26
  11,27
  12,28
  13,29
  14,30
  15,31

A PCI slot typically corresponds to a single NUMA node. For optimal
performance, a DPDK NIC and any instance utilizing the NIC should be
restricted to the same NUMA node and its respective memory. Ensuring
this behavior requires the use of flavors, host aggregates, and special
kernel parameters and Open vSwitch/DPDK configuration settings.

In this example, a single 10G NIC installed in PCI slot 2 is bound to NUMA
node0. Ideally, any instances utilizing the NIC would be limited to cores and
memory associated with NUMA node0. This means cores 0-7 and 16-23, and up to
48GB of RAM. In reality, however, some cores and RAM from NUMA node0 will be
reserved and made unavailable to instances. In addition, cores 8-15 and 24-31
associated with NUMA node1 should be made unavailable to instances. The
configuration to do just that will be covered later in this guide.

It is considered good practice to reserve a single physical core and its
respective virtual sibling from each NUMA node for normal (non-DPDK)
operating system functions. In addition, at least one physical core
(and sibling) from each NUMA node should be reserved for DPDK poll mode
driver (PMD) functions, even when a NIC(s) is bound to a single NUMA node.
The remaining cores can be reserved for virtual machine instances.

In this example, the breakdown would resemble the following:

```
| Reserved Cores         | Purpose               | node0     | node1 |
| ---------------------- | --------------------- | --------- | ----- |
| 0,8,16,24              | Host Operating System | 0,16      | 8,24  |
| 1,9,17,25              | DPDK PMDs             | 1,17      | 9,25  |
| 2-7,18-23              | Virtual Machines      | 2-7,18-23 | N/A   |
```

The variables are overrides used to define this configuration are discussed
in the following sections.

Hugepage configuration
~~~~~~~~~~~~~~~~~~~~~~

DPDK requires the configuration of hugepages, which is a mechanism by which
the Linux kernel can partition and address larger amounts of memory beyond
the basic page unit (4096 bytes). Huge pages are blocks of contiguous memory
that commonly come in 2MB and 1G sizes. The page tables used by 2MB pages
are suitable for managing multiple gigabytes of memory, whereas the page tables
of 1GB pages are preferred for scaling to terabytes of memory. DPDK requires
the use of 1GB pages.

A typical x86 system will have a Huge Page Size of 2048 kBytes (2MB). The
default huge page size may be found by looking at the output of /proc/meminfo:

.. code-block:: console

  # cat /proc/meminfo | grep Hugepagesize
  Hugepagesize: 2048 kB

The number of Hugepages can be allocated at runtime by modifying
``/proc/sys/vm/nr_hugepages`` or by using the ``sysctl`` command.

To view the current setting using the ``/proc`` entry:

.. code-block:: console

  # cat /proc/sys/vm/nr_hugepages
  0

To view the current setting using the ``sysctl`` command:

.. code-block:: console

  # sysctl vm.nr_hugepages
  vm.nr_hugepages = 0

To set the number of huge pages using ``/proc`` entry:

.. code-block:: console

  # echo 5 > /proc/sys/vm/nr_hugepages

To set the number of hugepages using sysctl:

.. code-block:: console

  # sysctl -w vm.nr_hugepages=5
  vm.nr_hugepages = 5

It may be necessary to reboot to be able to allocate the number of hugepages
that is needed. This is due to hugepages requiring large areas of contiguous
physical memory.

When 1G hugepages are used, they must be configured at boot time. The amount
of 1G hugepages that should be created will vary based on a few factors,
including:

* The total amount of RAM available in the system
* The amount of RAM required for the planned number of instances
* The number of NUMA nodes that will be used

The NUMA topology presented here corresponds to a host with 2x Intel Xeon 2450L
processors with 96GB of total RAM. The RAM is evenly split between the two NUMA
nodes. A DPDK NIC will be associated with a single NUMA node, and for optimal
performance any instance utilizing the DPDK NIC should be limited to the same
cores and memory associated with the NUMA node. On this example system,
both DPDK and instances can only utilize *up to* the 48GB of RAM associated
with NUMA node0, though some of that RAM will be utilized by the OS and other
tasks.

Of the 48GB of RAM available on NUMA node0, 32GB will be reserved for 1GB
hugepages to be consumed by DPDK PMDs and instances. Configuring hugepages
using kernel parameters results in the defined number of hugepages to be split
evenly across NUMA nodes. With the following kernel parameter, each NUMA node
will be assigned 32x 1G hugepages:

.. code-block:: console

  GRUB_CMDLINE_LINUX="... hugepagesz=1G hugepages=64"

Hugepages can be adjusted at runtime if necessary, but doing so is outside the
scope of this guide.

OpenStack-Ansible variables and overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ability to pin instances to certain cores is not new, and can be
accomplished using the ``vcpu_pin_set`` override seen here:

.. code-block:: console

  nova_nova_conf_overrides:
    DEFAULT:
      vcpu_pin_set: 2-7,18-23

This change can be added to the ``user_overrides.yml`` file for global
implementation, or to individual nodes in the ``openstack_user_config.yml``
file as shown here:

.. code-block:: console

  compute_hosts:
    compute01:
      ip: 172.29.236.200
      container_vars:
        ...
        nova_nova_conf_overrides:
          DEFAULT:
            vcpu_pin_set: 2-7,18-23

Cores reserved for host operating system functions (non-DPDK) must be converted
to a hexidecimal mask and defined using the ``ovs_dpdk_lcore_mask`` override.
To convert to a hex mask you must first establish the binary mask of chosen
cores using the following table:

```
| 31 | 30 | . | 24 | 23 | . | 17 | 16 | 15 | . | 9  | 8  | 7  | . | 1  | 0  |
| -- | -- | - | -- | -- | - | -- | -- | -- | - | -- | -- | -- | - | -- | -- |
| 0  | 0  | . | 1  | 0  | . | 0  | 1  | 0  | . | 0  | 1  | 0  | . | 0  | 1  |
```

The ellipses represent cores not shown. The binary mask for cores 0,8,16,24
can be determined in the following way:

.. code-block:: console

  00000001000000010000000100000001

The hexidecimal representation of that binary value is ``0x1010101``. Set
the ``ovs_dpdk_lcore_mask`` override accordingly in the ``user_variables.yml``
file or ``openstack_user_config.yml``:

.. code-block:: console

  ovs_dpdk_lcore_mask: 1010101

The mask for cores 1,9,17,25 reserved for DPDK PMDs can be determined in
a similar fashion. The table would resemble the following:

```
| 31 | 30 | . | 25 | 24 | . | 17 | 16 | 15 | . | 9  | 8  | 7  | . | 1  | 0  |
| -- | -- | - | -- | -- | - | -- | -- | -- | - | -- | -- | -- | - | -- | -- |
| 0  | 0  | . | 1  | 0  | . | 1  | 0  | 0  | . | 1  | 0  | 0  | . | 1  | 0  |
```

The ellipses represent cores not shown. The binary mask for cores 1,9,17,254
can be determined in the following way:

.. code-block:: console

  00000010000000100000001000000010

The hexidecimal representation of that binary value is ``0x2020202``. Set
the ``ovs_dpdk_pmd_cpu_mask`` override accordingly in the
``user_variables.yml`` file or ``openstack_user_config.yml``:

.. code-block:: console

  ovs_dpdk_pmd_cpu_mask: 2020202

Additional variables should be set, including:

* ovs_dpdk_driver
* ovs_dpdk_pci_addresses
* ovs_dpdk_socket_mem

The default value for ``ovs_dpdk_driver`` is ``vfio-pci``. Overrides can be
set globally or on a per-host basis.

.. note::

  Please consult the DPDK Network Interface Controller Driver `documentation
  <https://doc.dpdk.org/guides/nics/index.html>`_ for more inforation on
  supported network drivers for DPDK.

The value for ``ovs_dpdk_pci_addresses`` is the PCI bus address of the NIC
port(s) associated with the DPDK NIC. In this example, the DPDK NIC is
identified as address ``0000:03:00``. The individual interfaces are
``0000:03:00.0`` and ``0000:03:00.1``, respectively. The variable
``ovs_dpdk_pci_addresses`` is a list, and both values can be defined like so:

.. code-block:: console

  ovs_dpdk_pci_addresses:
    - 0000:03:00.0
    - 0000:03:00.1

The value for ``ovs_dpdk_socket_mem`` will vary based on the number of NUMA
nodes, number of NICs per NUMA node, and the MTU. The default value assumes
a single NUMA node and associates a single 1G hugepage to DPDK that can
handle a 1500 MTU. When multiple NUMA nodes are available, even with a single
NIC, the following should be set:

.. code-block:: console

  ovs_dpdk_socket_mem: "1024,1024"

For systems using a single NUMA node of a dual-NUMA system and a 9000 MTU, the
following can be set:

.. code-block:: console

  ovs_dpdk_socket_mem: "3072,1024"

Determing socket memory required involves calculations that are out of the
scope of this guide.

Flavor configuration
~~~~~~~~~~~~~~~~~~~~

Instances that connect to a DPDK-accelerated Open vSwitch must be configured to
utilize large (1G) hugepages by way of custom flavor attributes.

The ``hw:mem_page_size`` property can be set on a new or existing flavor to
enable this functionality:

.. code-block:: console

  openstack flavor set m1.small --property hw:mem_page_size=large

NOTE: If small page size is used, or no page size is set, the interface may
appear in the instance but will not be functional.

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
``/etc/openstack_deploy/openstack_user_config.yml`` that define one or more
Neutron provider bridges and related configuration:

.. note::

  Bridges specified here will be created automatically. If *network_interface*
  is defined, the interface will be placed into the bridge automatically
  as a *DPDK-accelerated* interface.

.. code-block:: yaml

  - network:
      container_bridge: "br-provider"
      container_type: "veth"
      type: "vlan"
      range: "101:200,301:400"
      net_name: "physnet1"
      network_interface: "eno49"
      group_binds:
        - neutron_openvswitch_agent

A *DPDK-accelerated* **bond** interface can be created by specifying a list
of member interfaces using `network_bond_interfaces`. The bond port will
be created automatically and added to the respective bridge in OVS:

.. code-block:: yaml

  - network:
      container_bridge: "br-provider"
      container_type: "veth"
      type: "vlan"
      range: "101:200,301:400"
      net_name: "physnet1"
      network_bond_interfaces:
        - "0000:04:00.0"
        - "0000:04:00.1"
      group_binds:
        - neutron_openvswitch_agent

Additional OVS bond parameters can be specified using the following keys:

* bond_mode (Default: active-backup)
* lacp (Default: off)
* bond_downdelay (Default: 100)
* bond_updelay (Default: 100)

.. code-block:: yaml

  - network:
      container_bridge: "br-provider"
      container_type: "veth"
      type: "vlan"
      range: "101:200,301:400"
      net_name: "physnet1"
      network_bond_interfaces:
        - "0000:04:00.0"
        - "0000:04:00.1"
      bond_mode: balance-tcp
      lacp: active
      bond_downdelay: 200
      bond_updelay: 200
      group_binds:
        - neutron_openvswitch_agent

For more information on possible values, visit:
`<https://docs.ansible.com/ansible/latest/collections/openvswitch/openvswitch/openvswitch_bond_module.html>`_

Set the following user variables in your
``/etc/openstack_deploy/user_variables.yml`` to enable the Open vSwitch driver
and DPDK support:

.. code-block:: yaml

  neutron_plugin_type: ml2.ovs
  neutron_ml2_drivers_type: "vlan"

  # Enable DPDK support
  ovs_dpdk_support: True

  # Add these overrides or set on per-host basis in openstack_user_config.yml
  ovs_dpdk_pci_addresses:
    - "0000:04:00.0"
    - "0000:04:00.1"
  ovs_dpdk_lcore_mask: 1010101
  ovs_dpdk_pmd_cpu_mask: 2020202
  ovs_dpdk_socket_mem: "1024,1024"

.. note::

  Overlay networks are not supported on DPDK-enabled nodes at this time.

Post-installation
~~~~~~~~~~~~~~~~~

Once the playbooks have been run and OVS/DPDK has been configured, it may be
necessary to add a physical interface to the provider bridge before networking
can be fully established *if* `network_interface` or `network_bond_interfaces`
have not been defined.

On compute nodes, the following command can be used to attach a NIC port
``0000:04:00.0`` to the provider bridge ``br-provider``:

.. code-block:: console

  ovs-vsctl add-port br-provider 0000:04:00.0 -- set interface 0000:04:00.0 type=dpdk options:dpdk-devargs=0000:04:00.0

Additionally, it may be necessary to make post-installation adjustments to
interface queues or other parameters to avoid errors within Open vSwitch:

.. code-block:: console

  ovs-vsctl set interface 0000:04:00.0 options:n_txq=5
  ovs-vsctl set interface 0000:04:00.0 options:n_rxq=5

The command(s) can be adjusted according to your configuration.

.. warning::

  Adding multiple ports to a bridge may result in bridging loops unless
  bonding is configured.
