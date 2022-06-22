===============================
OpenStack-Ansible Galera server
===============================

Ansible role to install and configure a Galera cluster powered by MariaDB

To clone or view the source code for this repository, visit the role repository
for `galera_server <https://github.com/openstack/openstack-ansible-galera_server>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required variables
~~~~~~~~~~~~~~~~~~

To use this role, define the following variables:

.. code-block:: yaml

    galera_root_password: secrete


Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
