=================================
Blazar role for OpenStack-Ansible
=================================

:tags: openstack, blazar, cloud, ansible
:category: \*nix

To clone or view the source code for this repository, visit the role repository
for `os_blazar <https://github.com/openstack/openstack-ansible-os_blazar>`_.

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
