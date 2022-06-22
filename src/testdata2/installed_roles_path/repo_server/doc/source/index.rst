=============================
OpenStack-Ansible Repo Server
=============================

Ansible role that deploys a repository server for python packages, git
sources and package caching for deb/rpm.

To clone or view the source code for this repository, visit the role repository
for `repo_server <https://github.com/openstack/openstack-ansible-repo_server>`_.

Default variables
~~~~~~~~~~~~~~~~~
.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required variables
~~~~~~~~~~~~~~~~~~

None.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
