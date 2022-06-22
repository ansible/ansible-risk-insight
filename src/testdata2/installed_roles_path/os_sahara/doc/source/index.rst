=============================
OpenStack-Ansible sahara role
=============================

.. toctree::
   :maxdepth: 2

   configure-sahara.rst

This role installs the following Systemd services:

    * sahara-api
    * sahara-engine

To clone or view the source code for this repository, visit the role repository
for `os_sahara <https://github.com/openstack/openstack-ansible-os_sahara>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

To use this role, define the following variables:

.. code-block:: yaml

    sahara_galera_address
    sahara_container_mysql_password
    sahara_service_password
    sahara_rabbitmq_password

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
~~~~

This role supports two tags: ``sahara-install`` and ``sahara-config``.
The ``sahara-install`` tag can be used to install and upgrade. The
``sahara-config`` tag can be used to manage configuration.
