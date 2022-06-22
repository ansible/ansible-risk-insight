========================
Team and repository tags
========================

.. image:: http://governance.openstack.org/badges/openstack-ansible-os_adjutant.svg
    :target: http://governance.openstack.org/reference/tags/index.html

.. Change things from this point on

OpenStack-Ansible Adjutant
############################
:tags: openstack, adjutant, cloud, ansible
:category: \*nix

This Ansible role installs and configures OpenStack adjutant.

This role will install the following Upstart services:
    * adjutant-api
    * adjutant-processor

Required Variables
==================

.. code-block:: yaml

    adjutant_service_password
    adjutant_rabbitmq_password
    adjutant_galera_password
    adjutant_galera_address

Example Playbook
================

.. code-block:: yaml

    - name: Install adjutant server
      hosts: adjutant_all
      user: root
      roles:
        - { role: "os_adjutant", tags: [ "os-adjutant" ] }
      vars:
        external_lb_vip_address: 172.16.24.1
        internal_lb_vip_address: 192.168.0.1
        adjutant_galera_address: "{{ internal_lb_vip_address }}"
        adjutant_galera_password: "SuperSecretePassword1"
        adjutant_service_password: "SuperSecretePassword2"
        adjutant_rabbitmq_password: "SuperSecretePassword3"
