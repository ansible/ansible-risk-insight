etcd Ansible Role
##################################

Ansible role to install and configure etcd clusters and proxies

.. image:: https://github.com/noonedeadpunk/ansible-role-etcd/actions/workflows/main.yml/badge.svg?branch=master

Default Variables
=================

.. literalinclude:: defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required Variables
==================

None

Example Playbook
================

.. code-block:: yaml

    - name: Install etcd
      hosts: etcd
      user: root
      roles:
        - { role: "etcd" }
