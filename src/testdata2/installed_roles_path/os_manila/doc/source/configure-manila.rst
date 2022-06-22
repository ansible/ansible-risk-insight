==============================================================
Configuring the Shared File System (manila) service (optional)
==============================================================

By default the Shared File System (manila) service does not deploy any
backend.  This role expects you to define the backend you intend on using.
The following sections describe example configurations for various
manila backends.

Default share type
~~~~~~~~~~~~~~~~~~

It is required to define one of the ``manila_backends`` as the default
share type.

.. code::

     manila_default_share_type: SHARE_TYPE_NAME

Replce ``SHARE_TYPE_NAME`` with the name of the default backend.

LVM backend
~~~~~~~~~~~

The LVM backend allows provisioning of logical volumes and configuriung a
local NFS server to serve those volumes as shares.

.. note::

   Using the LVM backend results in a Single Point of Failure

#. For each storage node, add one ``manila_backends`` block underneath
   the ``container_vars`` section.  ``container_vars`` are used to allow
   container/host individualized configuration.  Each manila back end is
   defined with a unique key.  For example, ``nfs-share1``.
   This later represents a unique manila backend and share type.

   .. code-block:: yaml

       container_vars:
         manila_enabled_share_protocols: NFS
         manila_backends:
           nfs-share1:

#. Configure the appropriate share protocols.  For the LVM backend you
   will need a minimu of ``NFS``.

   .. code-block:: yaml

       container_vars:
         manila_enabled_share_protocols: NFS

#. Configure the appropriate manila share backend name:

   .. code-block:: yaml

      share_backend_name: NFS_SHARE1

#. Configure the appropriate manila LVM driver:

   .. code-block:: yaml

      share_driver: manila.share.drivers.lvm.LVMShareDriver
      lvm_share_volume_group: LVM_VOLUME_GROUP

   Replace  ``LVM_VOLUME_GROUP`` with the name of the LVM
   volume group manila should use to provision shares.

#. Configure whether this backend manages share servers.  The only
   current supported option for this role is ``False`` as
   deploying a manila backend that manages share servers has not been
   tested yet.

   .. code-block:: yaml

      driver_handles_share_servers: False

#. Configure the IP address/es or hostnames of the share server.

   .. code-block:: yaml

      lvm_share_export_ips: "IP_ADDRESS"

   Replace ``IP_ADDRESS`` with a comma separated string of one or more IP
   addresses or hostnames where the nfs shares will be exported from.

The following is a full configuration example of a manila LVM backend
named NFS_SHARE1.  The manila playbooks will automatically add a custom
``share-type`` and ``nfs-share1`` as in this example:

   .. code-block:: yaml

    container_vars:
       manila_default_share_type: nfs-share1
       manila_enabled_share_protocols: NFS
       manila_backends:
         limit_container_types: manila_share
         nfs-share1:
           share_backend_name: NFS_SHARE1
           share_driver: manila.share.drivers.lvm.LVMShareDriver
           driver_handles_share_servers: False
           lvm_share_volume_group: manila-shares
           lvm_share_export_ips: 172.29.236.100
