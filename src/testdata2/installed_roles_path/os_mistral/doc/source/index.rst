==============================
OpenStack-Ansible mistral role
==============================

This role installs the following Systemd services:

    * mistral-api
    * mistral-engine
    * mistral-executor
    * mistral-notifier

To clone or view the source code for this repository, visit the role repository
for `os_mistral <https://github.com/openstack/openstack-ansible-os_mistral>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
~~~~

This role supports two tags: ``mistral-install`` and ``mistral-config``.
The ``mistral-install`` tag can be used to install and upgrade. The
``mistral-config`` tag can be used to manage configuration.
