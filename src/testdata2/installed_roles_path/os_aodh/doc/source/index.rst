===============================
Aodh role for OpenStack-Ansible
===============================

.. toctree::
   :maxdepth: 2

   configure-aodh.rst

To clone or view the source code for this repository, visit the role repository
for `os_aodh <https://github.com/openstack/openstack-ansible-os_aodh>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

To use this role, define the following variables:

.. code-block:: yaml

   # Needed for aodh to talk to MongoDB
   aodh_container_db_password: "secrete"
   # Password used for Keystone aodh service user
   aodh_service_password: "secrete"
   # Needed for aodh to talk to memcached
   memcached_servers: 127.0.0.1
   memcached_encryption_key: "some_key"
   # Needed for aodh to locate and connect to Oslo.Messaging
   aodh_oslomsg_rpc_transport: rabbit
   aodh_oslomsg_rpc_password: "secrete"
   aodh_oslomsg_rpc_servers: "10.100.100.2"
   aodh_oslomsg_rpc_use_ssl: true
   aodh_oslomsg_rpc_port: 5671
   aodh_oslomsg_notify_transport: rabbit
   aodh_oslomsg_notify_password: "secrete"
   aodh_oslomsg_notify_servers: "10.100.100.2"
   aodh_oslomsg_notify_use_ssl: true
   aodh_oslomsg_notify_port: 5671
   # Needed to setup the aodh service in Keystone
   keystone_admin_user_name: admin
   keystone_admin_tenant_name: admin
   keystone_auth_admin_password: "SuperSecretePassword"
   keystone_service_adminuri_insecure: false
   keystone_service_internaluri_insecure: false
   keystone_service_internaluri: "http://1.2.3.4:5000"
   keystone_service_internalurl: "{{ keystone_service_internaluri }}/v3"
   keystone_service_adminuri: "http://5.6.7.8:5000"
   keystone_service_adminurl: "{{ keystone_service_adminuri }}/v3"

Tags
~~~~

This role supports two tags: ``aodh-install`` and
``aodh-config``. The ``aodh-install`` tag can be used to install
and upgrade. The ``aodh-config`` tag can be used to maintain the
configuration of the service.
