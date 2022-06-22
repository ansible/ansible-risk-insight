BIRD Ansible Role
##################################

Ansible role to install and configure BIRD BGP daemon

.. image:: https://travis-ci.org/logan2211/ansible-bird.svg?branch=master
    :target: https://travis-ci.org/logan2211/ansible-bird

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

    - name: Install BIRD
      hosts: bird
      user: root
      roles:
        - { role: "bird" }
