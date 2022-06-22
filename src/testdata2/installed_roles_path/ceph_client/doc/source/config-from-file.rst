.. _configuration-from-files:

==============================
Ceph keyring from file example
==============================

OpenStack-Ansible (OSA) allows to deploy an OpenStack environment that uses an
existing Ceph cluster for block storage for images, volumes and instances.
Interaction with the Ceph cluster is normally done using SSH to Ceph MONs.
To avoid the SSH access to the Ceph cluster nodes all necessary client
configurations can be read from files. This example describes what these files
need to contain.

This example has just a single main requirement. You need to configure a
storage network in your OpenStack environment. Both Ceph services - the MONs
and the OSDs - need to be connected to this storage network, too. On the
OpenStack side you need to connect the affected services to the storage
network. Glance to store images in Ceph, Cinder to create volumes in Ceph and
in most cases the compute nodes to use volumes and maybe store ephemeral discs
in Ceph.

Network configuration assumptions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following CIDR assignments are used for this environment.

+-----------------------+-----------------+
| Network               | CIDR            |
+=======================+=================+
| Storage Network       | 172.29.244.0/22 |
+-----------------------+-----------------+

IP assignments
--------------

The following host name and IP address assignments are used for this
environment.

+------------------+----------------+
| Host name        | Storage IP     |
+==================+================+
| ceph1            | 172.29.244.18  |
+------------------+----------------+
| ceph2            | 172.29.244.19  |
+------------------+----------------+
| ceph3            | 172.29.244.20  |
+------------------+----------------+

Configuration
~~~~~~~~~~~~~

Environment customizations
--------------------------

For a ceph environment, you can run the ``cinder-volume`` in a container. By
default ``cinder-volume`` runs on the host. See
`here <https://docs.openstack.org/openstack-ansible/latest/user/prod/example.html#environment-customizations>`_
an example how to a service in a container.

User variables
--------------

The ``/etc/openstack_deploy/user_variables.yml`` file defines the global
overrides for the default variables.

For this example environment, we configure an existing Ceph cluster, that we
want the OpenStack environment to connect to. Your
``/etc/openstack_deploy/user_variables.yml`` must have the
following content to configure ceph for images, volumes and instances. If not
all necessary block storages should be provided from the Ceph backend, do only
include the block storage you want to store in Ceph:

.. literalinclude:: ../../examples/user_variables.yml.ceph-config.example

Ceph keyrings
-------------

With the above settings in the ``/etc/openstack_deploy/user_variables.yml`` we
configured to read the credentials for accessing the Ceph cluster in the
``/etc/openstack_deploy/ceph-keyrings/`` directory. We need to place now the
keyring files for Ceph credentials into this directory. They need to be named
according to the ceph client names, e.g. ``glance.keyring`` according to
``glance_ceph_client: glance``. See the following example for the file
contents:

.. literalinclude:: ../../examples/ceph-keyrings/glance.keyring.example
