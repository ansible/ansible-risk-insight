==================================
Neutron role for OpenStack-Ansible
==================================

.. toctree::
   :maxdepth: 2

   configure-network-services.rst
   app-openvswitch.rst
   app-openvswitch-asap.rst
   app-openvswitch-dvr.rst
   app-openvswitch-dpdk.rst
   app-openvswitch-sfc.rst
   app-ovn.rst
   app-nuage.rst
   app-nsx.rst
   app-calico.rst
   app-opendaylight.rst
   app-genericswitch.rst

:tags: openstack, neutron, cloud, ansible
:category: \*nix

This role installs the following Systemd services:

* neutron-server
* neutron-agents

To clone or view the source code for this repository, visit the role repository
for `os_neutron <https://github.com/openstack/openstack-ansible-os_neutron>`_.

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

This role supports two tags: ``neutron-install`` and
``neutron-config``. The ``neutron-install`` tag can be used to install
and upgrade. The ``neutron-config`` tag can be used to maintain the
configuration of the service.
