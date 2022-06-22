==========================
OpenStack-Ansible PKI role
==========================

This role installs a PKI infrastructure for maintaining a Root CA and
creating server certificates as required to enable secure communication
between components in a deployment.

To clone or view the source code for this repository, visit the role repository
for `pki <https://opendev.org/openstack/ansible-role-pki>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.


Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
