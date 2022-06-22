========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/openstack-ansible-os_cloudkitty.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

OpenStack-Ansible CloudKitty
############################
:tags: openstack, cloudkitty, cloud, ansible
:category: \*nix

This Ansible role installs and configures OpenStack cloudkitty.

This role will install the following Upstart services:
    * cloudkitty-api
    * cloudkitty-processor

Required Variables
==================

.. code-block:: yaml

   external_lb_vip_address: 172.16.24.1
   internal_lb_vip_address: 192.168.0.1
   cloudkitty_galera_address: "{{ internal_lb_vip_address }}"
   cloudkitty_container_mysql_password: "SuperSecretePassword1"
   cloudkitty_service_password: "SuperSecretePassword2"
   cloudkitty_rabbitmq_password: "SuperSecretePassword3"

Example Playbook
================

.. code-block:: yaml

    - name: Install cloudkitty service
      hosts: cloudkitty_all
      user: root
      roles:
        - { role: "os_cloudkitty", tags: [ "os-cloudkitty" ] }
      vars:
        external_lb_vip_address: 172.16.24.1
        internal_lb_vip_address: 192.168.0.1
        cloudkitty_galera_address: "{{ internal_lb_vip_address }}"
        cloudkitty_container_mysql_password: "SuperSecretePassword1"
        cloudkitty_service_password: "SuperSecretePassword2"
        cloudkitty_oslomsg_rpc_password: "SuperSecretePassword3"
        cloudkitty_oslomsg_notify_password: "SuperSecretePassword4"

Documentation for the project can be found at:
  https://docs.openstack.org/openstack-ansible-os_cloudkitty/latest/

Release notes for the project can be found at:
  https://docs.openstack.org/releasenotes/openstack-ansible-os_cloudkitty/

The project source code repository is located at:
  https://opendev.org/openstack/openstack-ansible-os_cloudkitty/

The project home is at:
  https://launchpad.net/openstack-ansible

The project bug tracker is located at:
  https://bugs.launchpad.net/openstack-ansible
