=============================
OpenStack-Ansible glance role
=============================

.. toctree::
   :maxdepth: 2

   configure-glance.rst

This role installs the following Systemd services:

    * glance-api

To clone or view the source code for this repository, visit the role repository
for `os_glance <https://github.com/openstack/openstack-ansible-os_glance>`_.

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

This role supports two tags: ``glance-install`` and ``glance-config``.
The ``glance-install`` tag can be used to install and upgrade. The
``glance-config`` tag can be used to manage configuration.
