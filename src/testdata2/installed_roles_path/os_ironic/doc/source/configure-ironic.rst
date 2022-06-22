======================================================
Configuring the Bare Metal (Ironic) Service (optional)
======================================================

.. note::

   This feature is experimental at this time and has not been fully
   production tested.

Ironic is an OpenStack project which provisions bare metal (as opposed to
virtual) machines by leveraging common technologies such as PXE boot and IPMI
to cover a wide range of hardware, while supporting pluggable drivers to allow
vendor-specific functionality to be added.

OpenStack's Ironic project makes physical servers as easy to provision as
virtual machines in a cloud.

OpenStack-Ansible Deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The use of Ironic within an OpenStack deployment leverages Nova to
deploy baremetal instances when an ``openstack server create`` command is
issued using a baremetal flavor. So, in addition to Ironic API services,
a Nova compute service using an Ironic compute driver (as opposed to
libvirt) must be configured. The playbooks can automatically deploy
this service when the inventory is configured accordingly.

To deploy Ironic, populate the respective groups within
``openstack_user_config.yml``:

.. code-block::

    ironic-infra_hosts: *infrastructure_hosts
    ironic-compute_hosts: *infrastructure_hosts

With the inventory updated, Ironic API and conductor services
will be deployed on the infra/controller nodes, along with a ``nova-compute``
service configured for use with Ironic.

OpenStack-Ansible is configured to support PXE-based deployments by default.
To enable the use of iPXE, which uses HTTP instead of TFTP for the full
deployment, add the following override:

.. code-block::

    ironic_ipxe_enabled: yes

.. note::

   With iPXE enabled, PXE is used to bootstrap into the iPXE loader.
   Deployment times are considerably faster with iPXE vs PXE, and its
   configuration is highly recommended. When iPXE is enabled, a web
   server is deployed on the conductor node(s) to host images and files.

Some drivers of the Baremetal service (in particular, any drivers using Direct
deploy or Ansible deploy interfaces, and some virtual media drivers) require
target user images to be available over clean HTTP(S) URL with NO
authentication involved (neither username/password-based, nor token-based).

The default deploy method relies on Swift to provide this functionality. If
Swift is not available in your environment, then the following override can
provide similar functionality by using the web server deployed the conductor
node(s) (see ``ironic_ipxe_enabled``):

.. code-block::

    ironic_enable_web_server_for_images: yes

The Ironic ``ipmi`` hardware driver is enabled by default. Vendor-specific
drivers, including iLO and DRAC, are available for use with supported
hardware. OpenStack-Ansible provides a set of drivers with pre-configured
hardware, boot, deploy, inspect, management, and power characteristics,
including:

* agent_ilo
* agent_ipmitool
* agent_ipmitool_socat
* agent_irmc
* agent_ucs
* pxe_agent_cimc
* pxe_drac
* pxe_drac_inspector
* pxe_ilo
* pxe_ipmitool
* pxe_ipmitool_socat
* pxe_irmc
* pxe_snmp
* pxe_ucs

.. note::

    The characteristics of these drivers can be seen in further details
    by reviewing the ``ironic_driver_types`` variable in the Ironic role.

To enable iLO and DRAC drivers, along with IPMI, set the following override:

.. code-block:: bash

    ironic_drivers_enabled:
      - agent_ipmitool
      - pxe_ipmitool
      - agent_ilo
      - pxe_ilo
      - pxe_drac

Setup Neutron Networks for Use With Ironic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ironic supports two main network interfaces: ``flat`` and ``neutron``:

* | The ``flat`` interface places all provisioned nodes and nodes being
  | deployed into a single layer 2 network.
* | The ``neutron`` interface provides tenant-defined networking
  | (aka multi-tenancy) by integrating with Neutron, while also separating
  | tenant networks from the provisioning and cleaning provider networks.

With the ``flat`` network interface, inspection, cleaning, and provisioning
functions will be performed on the same ``flat`` provider network. All
baremetal nodes will share the same VLAN and network/subnet once deployed,
which may present security challenges to tenants and to the control plane.

With the ``neutron`` network interface, inspection, cleaning, provisioning,
and tenant networks can use distict VLANs. However, an ML2 plugin such as
``networking-generic-switch`` must be used to configure the respective
switchports when switching between functions.

`<https://docs.openstack.org/openstack-ansible-os_neutron/latest/app-genericswitch.html>`_

.. note::

    Both the ``flat`` and ``neutron`` network interfaces require a cleaning
    network to be defined in ``ironic.conf``. For ``flat`` deployments, the
    cleaning network will be the same as the deployment network.

Create a network and subnet to be used by the baremetal instance for cleaning,
provisioning, and post-deployment use:

.. code-block:: bash

    openstack network create \
    --provider-network-type flat \
    --provider-physical-network physnet1 \
    myBaremetalNetwork

    openstack subnet create \
    --network myBaremetalNetwork \
    --subnet-range 172.17.100.0/24 \
    myBaremetalNetworkSubnet

Set an override to define the cleaning network name:

.. code-block:: bash

    ironic_neutron_cleaning_network_name: "myBaremetalNetwork"

.. note::

    Ironic multi-tenancy is an advanced topic that requires the use of a
    compatible ML2 driver such as ``networking-generic-switch``.

.. important::

   Provisioning activities on baremetal instances require network access
   to the Ironic conductor (web) service and other OpenStack APIs. You must
   ensure routing exists between respective networks for deployments to
   succeed.

Building Ironic Images
~~~~~~~~~~~~~~~~~~~~~~

Bare Metal provisioning requires two sets of images: the deploy images and the
user images. The deploy images consist of a kernel and ramdisk image that are
used by Ironic to prepare the baremetal server for actual OS deployment,
whereas the user images are installed on the baremetal server to be used by
the end user.

For more information on building and uploading disk images for use with
Ironic, refer to the following documentation:

`<https://docs.openstack.org/ironic/latest/user/creating-images.html>`_
`<https://docs.openstack.org/ironic/latest/install/configure-glance-images.html>`_

There are two types of user images:

* Partition Images
* Whole Disk Images

For your convenience, the following steps have been provided to demonstrate
creating partition-based images.

.. note::

    Images created using ``diskimage-builder`` must be built outside of an
    LXC container. For this process, use one of the physical hosts within
    the environment or a virtual machine.

#. Install the necessary pre-requisites:

   .. code-block:: bash

      apt install qemu uuid-runtime curl


#. Install the ``disk-imagebuilder`` package:

   .. code-block:: bash

      pip install diskimage-builder

   .. important::

      Only use the ``--isolated`` flag if you are building on a node
      deployed by OpenStack-Ansible, otherwise pip will not
      resolve the external package.

#. Create Ubuntu Focal kernel, ramdisk, and user images:

   .. code-block:: bash

      export IMAGE_NAME=my-image
      export DIB_RELEASE=focal
      export DIB_CLOUD_INIT_DATASOURCES="Ec2, ConfigDrive, OpenStack"
      disk-image-create ubuntu baremetal dhcp-all-interfaces grub2 -o ${IMAGE_NAME}

#. Upload the created user images into the Image (Glance) Service:

   .. code-block:: bash

      # Kernel image:
      openstack image create my-image.kernel \
      --public \
      --disk-format aki \
      --container-format aki \
      --file my-image.vmlinuz

      # Ramdisk image
      openstack image create my-image.initrd \
      --public \
      --disk-format ari \
      --container-format ari \
      --file my-image.initrd

      # User image
      openstack image create my-image \
      --public \
      --disk-format qcow2 \
      --container-format bare \
      --property kernel_id=<kernel image uuid> \
      --property ramdisk_id=<ramdisk image uuid> \
      --file my-image.qcow2

.. note::

      When a baremetal instance is provisioned using a partition-based
      image, the kernel and ramdisk images will be used for PXE when the
      ``local`` boot capability is not available.

Creating an Ironic Flavor
~~~~~~~~~~~~~~~~~~~~~~~~~

The use of flavors are necessary when creating instances using Nova,
and baremetal flavors should be used when targeting baremetal nodes
for instances. The properties of the flavor, along with the defined
resource class, are useful to the scheduler when scheduling against
libvirt or ironic compute services.

As an example, imagine an Ironic deployment has the following nodes:

.. code-block:: bash

    - node-1:
      resource_class: ironic-gold
      properties:
        cpus: 32
        memory_mb: 32768
        capabilities:
          boot_mode: uefi,bios
    - node-2:
      resource_class: ironic-silver
      properties:
        cpus: 16
        memory_mb: 16384

The operator might define the flavors as such:

.. code-block:: bash

    - baremetal-gold
      resources:
        ironic-gold: 1
      extra_specs:
        capabilities: boot_mode:bios
    - baremetal-gold-uefi
      resources:
        ironic-gold: 1
      extra_specs:
        capabilities: boot_mode:uefi
    - baremetal-silver
      resources:
        ironic-silver: 1

A user booting an instance with either the baremetal-gold or
baremetal-gold-uefi flavor would land on node-1, because capabilities can
still be passed down to ironic, and the resource_class on the node matche
what is required by flavor. The baremetal-silver flavor would match node-2.

.. note::

    A flavor can request exactly one instance of a bare metal resource class.

When creating a baremetal flavor, it’s useful to add the RAM and
CPU properties as a convenience to users, although they are not used for
scheduling. In addition, the DISK property is also not used for scheduling,
but is still used to determine the root partition size.

.. code-block:: bash

    openstack flavor create \
    --ram 32768 \
    --vcpu 32 \
    --disk 120 \
    baremetal-gold

After creation, associate each flavor with one custom resource class. The name
of a custom resource class that corresponds to a node’s resource class
(in the Bare Metal service) is:

* the bare metal node’s resource class all upper-cased
* prefixed with ``CUSTOM_``
* all punctuation replaced with an underscore

.. code-block:: bash

    openstack flavor set \
    --property resources:CUSTOM_IRONIC_GOLD=1 \
    baremetal-gold

.. note::

   Ensure the resource class defined in the flavor matches that
   of the baremetal node, otherwise, the scheduler will not find eligible
   hosts. In the example provided, the resource class is ``ironic-gold``.

Another set of flavor properties must be used to disable scheduling based on
standard properties for a bare metal flavor:

.. code-block:: bash

    openstack flavor set --property resources:VCPU=0 baremetal-gold
    openstack flavor set --property resources:MEMORY_MB=0 baremetal-gold
    openstack flavor set --property resources:DISK_GB=0 baremetal-gold

Lastly, a ``boot_option`` capability can be set to speed up booting after
the deployment:

.. code-block:: bash

    openstack flavor set --property capabilities:'boot_option=local' baremetal-gold

.. note::

    Specifying the ``local`` boot option allows the deployed baremetal
    instance to boot directly to disk instead of network.

Enrolling Ironic Nodes
~~~~~~~~~~~~~~~~~~~~~~

Enrolling baremetal nodes makes then available to the Ironic service. The
properties of a given node will allow Ironic to determine how an image should
be deployed on the node, including using IPMI or vendor-specific out-of-band
interfaces. Some properties are optional, and may rely on defaults set by
the operator or within OpenStack-Ansible. Others are required, and may be
noted as such.

Some things should be known about the baremetal node prior to enrollment,
including:

* Node Name
* Driver
* Deploy Interface (based on driver)
* Provisioning Interface (MAC Address)
* IPMI or OOB Credentials
* OOB Management IP
* Deploy Kernel Image UUID (from Glance)
* Deploy Ramdisk Image UUID (from Glance)
* Boot Mode (bios or uefi)
* Network Interface (flat or neutron)

.. note::

    Kernel and ramdisk images may be provided by the ``diskimage-builder``
    process, or may be downloaded from opendev.org:

    `<https://tarballs.opendev.org/openstack/ironic-python-agent/dib/>`_
    `<https://docs.openstack.org/ironic/latest/install/deploy-ramdisk.html>`_

.. important::

   The deploy kernel and ramdisk should be updated on a regular basis
   to match the OpenStack release of the underlying infrastructure. The
   Ironic Python Agent that runs on the ramdisk interfaces with Ironic
   APIs, and should be kept in sync.

To enroll a node, use the ``openstack baremetal node create`` command. The
example below demonstrates the creation of a baremetal node with the
following characteristics:

.. code-block:: bash

    node_name=baremetal01
    node_mac="f0:92:1c:0c:1f:88"    # MAC address of PXE interface (em1 as example)
    deploy_aki=ironic-deploy-aki    # Kernel image
    deploy_ari=ironic-deploy-ari    # Ramdisk image
    resource=ironic-gold            # Ironic resource class (matches flavor as CUSTOM_IRONIC_GOLD)
    phys_arch=x86_64
    phys_cpus=32
    phys_ram=32768
    phys_disk=270
    ipmi_username=root
    ipmi_password=calvin
    ipmi_address=172.19.0.22
    boot_mode=bios
    network_interface=flat

.. important::

   The Ironic conductor service must be able to communicate with the OOB IP
   address to perform provisioning functions.

.. code-block:: bash

   openstack baremetal node create \
     --driver ipmi \
     --deploy-interface direct \
     --driver-info ipmi_username=$ipmi_username \
     --driver-info ipmi_password=$ipmi_password \
     --driver-info ipmi_address=$ipmi_address \
     --driver-info deploy_kernel=`openstack image show $deploy_aki -c id |awk '/id / {print $4}'` \
     --driver-info deploy_ramdisk=`openstack image show $deploy_ari -c id |awk '/id / {print $4}'` \
     --property cpus=$phys_cpus \
     --property memory_mb=$phys_ram \
     --property local_gb=$phys_disk \
     --property cpu_arch=$phys_arch \
     --property capabilities='boot_option:local,disk_label:gpt' \
     --resource-class $resource \
     --network-interface $network_interface \
     --name $node_name

The node will first appear in an ``enroll`` state. To make it available for
provisioning, set the state to ``manage``, then ``available``:

.. code-block:: bash

    openstack baremetal node manage baremetal01
    openstack baremetal node provide baremetal01
    openstack baremetal node list --fit

    +--------------------------------------+-------------+---------------+-------------+--------------------+-------------+
    | UUID                                 | Name        | Instance UUID | Power State | Provisioning State | Maintenance |
    +--------------------------------------+-------------+---------------+-------------+--------------------+-------------+
    | c362890d-5d7a-4dc3-ad29-7dac0bf49344 | baremetal01 | None          | power off   | available          | False       |
    +--------------------------------------+-------------+---------------+-------------+--------------------+-------------+

Next, create a baremetal port using the ``openstack baremetal port create``
command:

.. code-block:: bash

    node_name=baremetal01
    node_mac="f0:92:1c:0c:1f:88"
    openstack baremetal port create $node_mac \
    --node `openstack baremetal node show $node_name -c uuid |awk -F "|" '/ uuid  / {print $3}'`

    +-----------------------+--------------------------------------+
    | Field                 | Value                                |
    +-----------------------+--------------------------------------+
    | address               | f0:92:1c:0c:1f:88                    |
    | created_at            | 2021-12-17T20:36:19+00:00            |
    | extra                 | {}                                   |
    | internal_info         | {}                                   |
    | is_smartnic           | False                                |
    | local_link_connection | {}                                   |
    | node_uuid             | c362890d-5d7a-4dc3-ad29-7dac0bf49344 |
    | physical_network      | None                                 |
    | portgroup_uuid        | None                                 |
    | pxe_enabled           | True                                 |
    | updated_at            | None                                 |
    | uuid                  | 44e5d872-ffa5-45f5-a5aa-7147c523e593 |
    +-----------------------+--------------------------------------+

.. note::

    The baremetal port is used to setup Neutron to provide DHCP services
    during provisioning. When the ``neutron`` network interface is used,
    the respective switchport can be managed by OpenStack.


Deploy a Baremetal Node Using Ironic
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Baremetal instances can be deployed using the ``openstack server create``
command and a baremetal flavor. Unless the image has been created with
support for passwords, an SSH key must be provided. The baremetal instance
relies on Neutron DHCP and metadata services, just like a virtual instance.

.. code-block:: bash

    openstack server create \
    --flavor baremetal-gold \
    --image focal-server-cloudimg-amd64 \
    --key-name myKey \
    --network myBaremetalNetwork \
    myBaremetalInstance

.. important::

   If you do not have an ssh key readily available, set one up with
   ``ssh-keygen`` and/or create one with ``openstack keypair create``.
   Otherwise, you will not be able to connect to the deployed instance.
