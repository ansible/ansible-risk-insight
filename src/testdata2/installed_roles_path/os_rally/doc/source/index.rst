================================
Rally role for OpenStack-Ansible
================================

This Ansible role installs and configures OpenStack Rally.

To clone or view the source code for this repository, visit the role repository
for `os_rally <https://github.com/openstack/openstack-ansible-os_rally>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

To use this role, the following variables must be defined:

* ``rally_galera_address``
* ``rally_galera_password``

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
