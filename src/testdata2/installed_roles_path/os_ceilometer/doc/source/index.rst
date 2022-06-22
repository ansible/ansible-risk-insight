=====================================
Ceilometer role for OpenStack-Ansible
=====================================

This Ansible role installs and configures OpenStack ceilometer.

Meter and notification storage is configured to use a MongoDB backend
by default. This role does not install and configure the MongoDB backend.
Deployers wishing to use MongoDB must install and configure it prior to
using this role and override ``ceilometer_connection_string`` variable with
MongoDB connection details.

Table of Contents
=================

.. toctree::
   :maxdepth: 2

   configure-ceilometer.rst

To clone or view the source code for this repository, visit the role repository
for `os_ceilometer <https://github.com/openstack/openstack-ansible-os_ceilometer>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

Tags
~~~~

This role supports two tags: ``ceilometer-install`` and
``ceilometer-config``. The ``ceilometer-install`` tag can be used to install
and upgrade. The ``ceilometer-config`` tag can be used to maintain the
configuration of the service.
