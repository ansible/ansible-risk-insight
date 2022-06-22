================================
OpenStack-Ansible HAProxy server
================================

.. toctree::
   :maxdepth: 2

   configure-haproxy.rst

This Ansible role installs the HAProxy Load Balancer service.

To clone or view the source code for this repository, visit the role repository
for `haproxy_server <https://github.com/openstack/openstack-ansible-haproxy_server>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required variables
~~~~~~~~~~~~~~~~~~

None.

Dependencies
~~~~~~~~~~~~

None.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
