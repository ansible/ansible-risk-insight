resolv.conf Ansible Role
##################################

Ansible role to configure system resolvers

.. image:: https://travis-ci.org/Logan2211/ansible-resolvconf.svg?branch=master
    :target: https://travis-ci.org/Logan2211/ansible-resolvconf

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

    - name: Install resolvconf
      hosts: all
      user: root
      roles:
        - { role: "resolvconf" }
