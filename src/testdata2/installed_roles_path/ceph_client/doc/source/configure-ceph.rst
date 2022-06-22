======================================
Configuring the Ceph client (optional)
======================================

Ceph is a massively scalable, open source, distributed storage system.

These links provide details on how to use Ceph with OpenStack:

* `Ceph Block Devices and OpenStack`_
* `Ceph - The De Facto Storage Backend for OpenStack`_ *(Hong Kong Summit
  talk)*
* `OpenStack Config Reference - Ceph RADOS Block Device (RBD)`_
* `OpenStack-Ansible and Ceph Working Example`_


.. _Ceph Block Devices and OpenStack: http://docs.ceph.com/docs/master/rbd/rbd-openstack/
.. _Ceph - The De Facto Storage Backend for OpenStack: https://www.openstack.org/summit/openstack-summit-hong-kong-2013/session-videos/presentation/ceph-the-de-facto-storage-backend-for-openstack
.. _OpenStack Config Reference - Ceph RADOS Block Device (RBD): https://docs.openstack.org/liberty/config-reference/content/ceph-rados.html
.. _OpenStack-Ansible and Ceph Working Example: https://www.openstackfaq.com/openstack-ansible-ceph/

.. note::

   Configuring Ceph storage servers is outside the scope of this documentation.

Authentication
~~~~~~~~~~~~~~

We recommend the ``cephx`` authentication method in the `Ceph
config reference`_. OpenStack-Ansible enables ``cephx`` by default for
the Ceph client. You can choose to override this setting by using the
``cephx`` Ansible variable:

.. code-block:: yaml

    cephx: False

Deploy Ceph on a trusted network if disabling ``cephx``.

.. _Ceph config reference: http://docs.ceph.com/docs/master/rados/configuration/auth-config-ref/

Configuration file overrides
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenStack-Ansible provides the ``ceph_conf_file`` variable. This allows
you to specify configuration file options to override the default
Ceph configuration:

.. code-block:: console

 ceph_conf_file: |
   [global]
   fsid = 4037aa5f-abde-4378-9470-f73dbd6ceaba
   mon_initial_members = mon1.example.local,mon2.example.local,mon3.example.local
   mon_host = 172.29.244.151,172.29.244.152,172.29.244.153
   auth_cluster_required = cephx
   auth_service_required = cephx
   auth_client_required = cephx

The use of the ``ceph_conf_file`` variable is optional. By default,
OpenStack-Ansible obtains a copy of ``ceph.conf`` from one of your Ceph
monitors. This transfer of ``ceph.conf`` requires the OpenStack-Ansible
deployment host public key to be deployed to all of the Ceph monitors. More
details are available here: `Deploying SSH Keys`_.

The following minimal example configuration sets nova and glance
to use ceph pools: ``ephemeral-vms`` and ``images`` respectively.
The example uses ``cephx`` authentication, and requires existing ``glance`` and
``cinder`` accounts for ``images`` and ``ephemeral-vms`` pools.

.. code-block:: console

    glance_default_store: rbd
    nova_libvirt_images_rbd_pool: ephemeral-vms

.. _Deploying SSH Keys: https://docs.openstack.org/project-deploy-guide/openstack-ansible/draft/targethosts-prepare.html#deploying-secure-shell-ssh-keys

For a complete example how to provide the necessary configuration for a Ceph
backend without necessary access to Ceph monitors via SSH please see
:ref:`configuration-from-files`.

Extra client configuration files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Deployers can specify extra Ceph configuration files to support
multiple Ceph cluster backends via the ``ceph_extra_confs`` variable.

.. code-block:: console

    ceph_extra_confs:
    -  src: "/opt/rdb-1.conf"
       dest: "/etc/ceph/rdb-1.conf"
    -  src: "/opt/rdb-2.conf"
       dest: "/etc/ceph/rdb-2.conf"

These config file sources must be present on the deployment host.

Alternatively, deployers can specify more options in ``ceph_extra_confs``
to deploy keyrings, ceph.conf files, and configure libvirt secrets.

.. code-block:: console

    ceph_extra_confs:
    -  src: "/etc/openstack_deploy/ceph2.conf"
       dest: "/etc/ceph/ceph2.conf"
       mon_host: 192.168.1.2
       client_name: cinder2
       keyring_src: /etc/openstack_deploy/ceph2.client.cinder2.keyring
       keyring_dest: /etc/ceph/ceph2.client.cinder2.keyring
       secret_uuid: '{{ cinder_ceph_client_uuid2 }}'
    -  src: "/etc/openstack_deploy/ceph3.conf"
       dest: "/etc/ceph/ceph3.conf"
       mon_host: 192.168.1.3
       client_name: cinder3
       keyring_src: /etc/openstack_deploy/ceph3.client.cinder3.keyring
       keyring_dest: /etc/ceph/ceph3.client.cinder3.keyring
       secret_uuid: '{{ cinder_ceph_client_uuid3 }}'

The primary aim of this feature is to deploy multiple ceph clusters as
cinder backends and enable nova/libvirt to mount block volumes from those
backends.  These settings do not override the normal deployment of
ceph client and associated setup tasks.

Deploying multiple ceph clusters as cinder backends requires the following
adjustments to each backend in ``cinder_backends``

.. code-block:: console

    rbd_ceph_conf: /etc/ceph/ceph2.conf
    rbd_pool: cinder_volumes_2
    rbd_user: cinder2
    rbd_secret_uuid: '{{ cinder_ceph_client_uuid2 }}'
    volume_backend_name: volumes2

The dictionary keys ``rbd_ceph_conf``, ``rbd_user``, and ``rbd_secret_uuid``
must be unique for each ceph cluster to used as a cinder_backend.

Monitors
~~~~~~~~

The `Ceph Monitor`_ maintains a master copy of the cluster map.
OpenStack-Ansible provides the ``ceph_mons`` variable and expects a list of
IP addresses for the Ceph Monitor servers in the deployment:

.. code-block:: yaml

  ceph_mons:
      - 172.29.244.151
      - 172.29.244.152
      - 172.29.244.153

Configure os_gnocchi with ceph_client
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If the os_gnocchi role is going to utilize the ceph_client role, the following
configurations need to be added to the user variable file:

.. code-block:: yaml

  ceph_extra_components:
    - component: gnocchi_api
      package: "{{ python_ceph_packages }}"
      client:
        - '{{ gnocchi_ceph_client }}'
      service: '{{ ceph_gnocchi_service_names }}'


.. _Ceph Monitor: http://docs.ceph.com/docs/master/rados/configuration/mon-config-ref/
