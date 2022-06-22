=================================
OpenStack-Ansible RabbitMQ server
=================================

This Ansible role deploys RabbitMQ. When multiple hosts are present in
the ``rabbitmq_all`` inventory group, a cluster is created.

Table of Contents
~~~~~~~~~~~~~~~~~

.. toctree::
   :maxdepth: 2

   configure-rabbitmq.rst


To clone or view the source code for this repository, visit the role repository
for `rabbitmq_server <https://github.com/openstack/openstack-ansible-rabbitmq_server>`_.

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

    # RabbitMQ cluster shared secret
    rabbitmq_cookie_token: secrete

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
