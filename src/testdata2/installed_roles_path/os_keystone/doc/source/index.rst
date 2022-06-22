===================================
Keystone role for OpenStack-Ansible
===================================

.. toctree::
   :maxdepth: 2

   configure-keystone.rst
   configure-federation.rst
   configure-federation-wrapper.rst
   configure-federation-sp.rst
   configure-federation-idp.rst
   configure-federation-mapping.rst

To clone or view the source code for this repository, visit the role repository
for `os_keystone <https://github.com/openstack/openstack-ansible-os_keystone>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.


Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

To use this role, define the following variables:

.. code-block:: yaml

    # hostname or IP of load balancer providing external network
    # access to Keystone
    external_lb_vip_address: 10.100.100.102

    # hostname or IP of load balancer providing internal network
    # access to Keystone
    internal_lb_vip_address: 10.100.100.102

    # password used by the keystone service to interact with Galera
    keystone_container_mysql_password: "YourPassword"

    keystone_auth_admin_password: "SuperSecretePassword"
    keystone_rabbitmq_password: "secrete"
    keystone_container_mysql_password: "SuperSecrete"

This list is not exhaustive at present. See role internals for further
details.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
~~~~

This role supports two tags: ``keystone-install`` and ``keystone-config``

The ``keystone-install`` tag can be used to install and upgrade.

The ``keystone-config`` tag can be used to maintain configuration of the
service.
