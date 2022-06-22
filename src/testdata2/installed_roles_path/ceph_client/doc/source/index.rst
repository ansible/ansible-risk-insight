=============================
OpenStack-Ansible Ceph client
=============================

.. toctree::
   :maxdepth: 2

   configure-ceph.rst
   config-from-file.rst

This Ansible role installs the Ceph operating system
packages used to interact with a Ceph cluster.

To clone or view the source code for this repository, visit the role repository
for `ceph_client <https://github.com/openstack/openstack-ansible-ceph_client>`_.

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
