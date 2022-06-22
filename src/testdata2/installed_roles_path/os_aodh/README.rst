========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/openstack-ansible-os_aodh.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

OpenStack Aodh
##############

Ansible role that installs and configures OpenStack Aodh as the alarm
functionality of Telemetry.

This role will install the following:
    * aodh-api
    * aodh-listener
    * aodh-evaluator
    * aodh-notifier

The role will configure Aodh to use MongoDB for data storage, but does
not install or configure MongoDB.

Default Variables
=================

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required Variables
==================

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

======================
OpenStack-Ansible Aodh
======================

Ansible role to install OpenStack Aodh.

Documentation for the project can be found at:
  https://docs.openstack.org/openstack-ansible-os_aodh/latest/

Release notes for the project can be found at:
  https://docs.openstack.org/releasenotes/openstack-ansible-os_aodh

The project source code repository is located at:
  https://opendev.org/openstack/openstack-ansible-os_aodh/

The project home is at:
  https://launchpad.net/openstack-ansible

The project bug tracker is located at:
  https://bugs.launchpad.net/openstack-ansible
