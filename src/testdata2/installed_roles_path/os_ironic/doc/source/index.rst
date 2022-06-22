======================================================
OpenStack-Ansible role for Bare Metal (ironic) service
======================================================

.. toctree::
   :maxdepth: 2

   configure-ironic.rst
   configure-inspector.rst

This is an OpenStack-Ansible role to deploy the Bare Metal (ironic)
service. See the `role-ironic spec`_ for more information.

.. _role-ironic spec: https://specs.openstack.org/openstack/openstack-ansible-specs/specs/mitaka/role-ironic.html


To clone or view the source code for this repository, visit the role repository
for `os_ironic <https://github.com/openstack/openstack-ansible-os_ironic>`_.

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

This role supports the ``ironic-install`` and ``ironic-config`` tags.
Use the ``ironic-install`` tag to install and upgrade. Use the
``ironic-config`` tag to maintain configuration of the service.
