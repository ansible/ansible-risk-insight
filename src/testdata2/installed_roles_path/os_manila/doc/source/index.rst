=================================
Manila role for OpenStack-Ansible
=================================

This Ansible role installs and configures OpenStack manila.

The following manila services are managed by the role:
    * manila_api
    * manila_scheduler
    * manila_share
    * manila_data (untested)

.. toctree::
   :maxdepth: 2

   configure-manila.rst

To clone of view the source code for this repository, visit the role repository
for `os_manila <https://github.com/openstack/openstack-ansible-os_manila>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
~~~~

This role supports two tags: ``manila-install`` and ``manila-config``

The ``manila-install`` tag can be used to install and upgrade.

The ``manila-config`` tag can be used to maintain configuration of the
service.
