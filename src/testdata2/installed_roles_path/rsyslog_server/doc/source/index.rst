========================
OpenStack rsyslog server
========================

Role to deploy rsyslog for use within OpenStack when deploying services using
containers.

Table of contents
~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   ops-logging.rst

To clone or view the source code for this repository, visit the role repository
for `rsyslog_server <https://github.com/openstack/openstack-ansible-rsyslog_server>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Required varibles
~~~~~~~~~~~~~~~~~

None

Example playbook
^^^^^^^^^^^^^^^^

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
