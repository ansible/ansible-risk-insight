===========================
OpenStack-Ansible Qdrouterd
===========================

This Ansible role deploys Qdrouterd. When multiple hosts are present in
the ``qdrouterd_all`` inventory group, a router mesh is created.

Table of Contents
~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

To clone or view the source code for this repository, visit the role repository
for `qdrouterd <https://github.com/openstack/ansible-role-qdrouterd>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.
