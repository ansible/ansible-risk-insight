========================
OpenStack rsyslog client
========================

Ansible role to deploy rsyslog for client use. This role will ship any and all
logs discovered in the ``rsyslog_client_log_dir`` directory to any valid
rsyslog target.  The role was designed to be used by OpenStack-Ansible by
leveraging multiple logging hosts via the **rsyslog_all** group. If that
inventory group is not defined additional log shipping targets can be defined
using ``rsyslog_client_user_defined_targets``

Table of contents
~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   ops-logging.rst

To clone or view the source code for this repository, visit the role repository
for `rsyslog_client <https://github.com/openstack/openstack-ansible-rsyslog_client>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required variables
~~~~~~~~~~~~~~~~~~

None

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
