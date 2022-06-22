=========================
OpenStack-Ansible Horizon
=========================

.. toctree::
   :maxdepth: 2

   configure-horizon.rst

This Ansible role installs and configures OpenStack Horizon served by the
Apache webserver. Horizon is configured to use Galera for session caching and
Memcached for other caching.

To clone or view the source code for this repository, visit the role repository
for `os_horizon <https://github.com/openstack/openstack-ansible-os_horizon>`_.

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

      horizon_galera_address: 10.100.100.101
      horizon_container_mysql_password: "SuperSecrete"
      horizon_secret_key: "SuperSecreteHorizonKey"

This list is not exhaustive. See role internals for further
details.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
====

This role supports two tags: ``horizon-install`` and ``horizon-config``.

The ``horizon-install`` tag can be used to install and upgrade.

The ``horizon-config`` tag can be used to manage configuration.
