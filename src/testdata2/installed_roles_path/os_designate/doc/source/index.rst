====================================
Designate role for OpenStack-Ansible
====================================

This Ansible role installs and configures OpenStack Designate.

This role will install the following services:
    * designate-api
    * designate-central
    * designate-worker
    * designate-producer
    * designate-mdns
    * designate-sink

The DNS servers Designate will interface with can be defined in the
``designate_pools_yaml`` variable. This is eventually written to the Designate
`pools.yaml <https://docs.openstack.org/designate/latest/admin/pools.html#managing-pools>`_
file.

To clone or view the source code for this repository, visit the role repository
for `os_designate <https://github.com/openstack/openstack-ansible-os_designate>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

This role needs the following variables defined:

.. code-block:: yaml

    designate_galera_address
    designate_galera_password
    designate_service_password
    designate_oslomsg_rpc_password
    designate_oslomsg_notify_password

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
~~~~

This role supports two tags: ``designate-install`` and ``designate-config``.
The ``designate-install`` tag can be used to install and upgrade. The
``designate-config`` tag can be used to maintain configuration of the service.
