Unbound Caching DNS Resolver Ansible Role
##################################

Ansible role to install and configure Unbound

.. image:: https://github.com/noonedeadpunk/ansible-unbound/actions/workflows/main.yml/badge.svg?branch=master

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

    - name: Install unbound
      hosts: unbound
      user: root
      roles:
        - { role: "unbound" }
