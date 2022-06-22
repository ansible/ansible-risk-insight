===================================
Congress role for OpenStack-Ansible
===================================

:tags: openstack, congress, cloud, ansible
:category: \*nix

To clone or view the source code for this repository, visit the role repository
for `os_congress <https://github.com/openstack/openstack-ansible-os_congress>`_.

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

- blazar-install
- blazar-config
