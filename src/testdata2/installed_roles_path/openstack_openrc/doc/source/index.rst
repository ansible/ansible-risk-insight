=============================
OpenStack-Ansible openrc file
=============================

This Ansible role creates the configuration files used by various
OpenStack CLI tools. For more information about these tools, see the
`OpenStack CLI Reference`_.

.. _OpenStack CLI Reference: https://docs.openstack.org/cli-reference/overview.html

To clone or view the source code for this repository, visit the role repository
for `openstack_openrc <https://github.com/openstack/openstack-ansible-openstack_openrc>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required variables
~~~~~~~~~~~~~~~~~~

To use this role, define the following variables:

.. code-block:: yaml

    keystone_service_adminuri_insecure: false
    keystone_service_internaluri_insecure: false
    openrc_os_password: secrete
    openrc_os_domain_name: Default

Tags
~~~~

This role supports two tags: ``openstack_openrc-install`` and
``openstack_openrc-config``. The ``openstack_openrc-install`` tag is only
used to setup the appropriate folders. The ``openstack_openrc-config`` tag
can be used to manage configuration.


Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
