=====================================
Scenario - Using PowerVM Nova plugin
=====================================

Prerequisites
~~~~~~~~~~~~~

In order to use the PowerVM OpenStack drivers with OpenStack-Ansible (OSA), the
following pre-requisites must be fulfilled:

 - At least one of the repo-build servers must be ppc64le. Can mix and match
   repo-build servers between x86 and ppc64le.

 - The compute nodes should be pre-configured for PowerVM with the NovaLink_
   feature.

 - The NovaLink Management VM needs at least one direct attach I/O card.
   OpenStack Ansible is currently able to deploy the PowerVM drivers when
   paired with the Open vSwitch agent. The traditional PowerVM Shared Ethernet
   Adapter networking agent is not yet supported.

 - The network topology on the NovaLink must match a supported OpenStack
   Ansible network configuration.

.. _NovaLink: http://www.ibm.com/support/knowledgecenter/POWER8/p8eig/p8eig_kickoff.htm?cp=POWER8


PowerVM usage
~~~~~~~~~~~~~

The Compute driver for OpenStack-Ansible should automatically detect that it
is of type PowerVM. If the user has specified a specific compute type, that
is applicable to the whole cloud. It is advised that the you allow OSA to
detect the appropriate compute node type.

The full set of configuration options for the PowerVM driver can be
found in the ``zun-powervm`` usage_.

.. _usage: https://zun-powervm.readthedocs.io/en/latest/devref/usage.html


Configuring storage
~~~~~~~~~~~~~~~~~~~

There are various storage back ends available for PowerVM such as local disk
and shared storage pools. For example, to enable local disk storage backed by
a logical volume group, you can set:

.. code-block:: yaml

    zun_zun_conf_overrides:
      powervm:
        disk_driver: localdisk
        volume_group_name: <<VOLUME GROUP NAME>>

To enable iSCSI as the volume attachment type, you can set the
``volume_adapter`` setting:

.. code-block:: yaml

    zun_zun_conf_overrides:
      powervm:
        volume_adapter: iscsi

The default volume attachment type for PowerVM is fibre channel.

Enabling VNC console
~~~~~~~~~~~~~~~~~~~~

PowerVM only supports connecting to instance consoles over VNC. As
OpenStack-Ansible defaults to Spice console, you must set the
``zun_console_type`` variable to enable NoVNC:

.. code-block:: yaml

    zun_console_type: novnc


Enabling configuration drive
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, PowerVM uses configuration drives to provide configuration
information to instances built by zun. To enable this support in
OpenStack-Ansible, you can set the ``zun_force_config_drive``
variable as documented in the `zun configuration instructions`_.

.. _zun configuration instructions: ./configure-zun.html#config-drive

Additionally, you can enable flat network injection by using the
``zun_zun_conf_overrides`` variable:

.. code-block:: yaml

    zun_zun_conf_overrides:
      DEFAULT:
        flat_injected: True

Enabling PowerVM RMC
~~~~~~~~~~~~~~~~~~~~

To enable PowerVM RMC_, IPv4/IPv6 dual-stack mode must be enabled. To do this,
you must set ``use_ipv6`` using the ``zun_zun_conf_overrides`` variable:

.. code-block:: yaml

    zun_zun_conf_overrides:
      DEFAULT:
        use_ipv6: True

.. _RMC: http://www.ibm.com/support/knowledgecenter/8284-22A/p8eig/p8eig_rmc.htm
