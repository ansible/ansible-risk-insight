=================================
Senlin role for OpenStack-Ansible
=================================


Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

To clone or view the source code for this repository, visit the role repository
for `os_senlin <https://opendev.org/openstack/openstack-ansible-os_senlin>`_.

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

This role supports two tags: ``senlin-install`` and
``senlin-config``. The ``senlin-install`` tag can be used to install
and upgrade. The ``senlin-config`` tag can be used to maintain the
configuration of the service.

Senlin client endpoints
~~~~~~~~~~~~~~~~~~~~~~~

When your VMs need to talk to your API, you might have to change the Senlin
config. By default Senlin is configured to use the internal API endpoints.
Should instances or created containers need to access the API (e.g.
Magnum, Senlin Signaling) the public endpoints will need to be used as in
the following example:

.. code-block:: yaml

    senlin_senlin_conf_overrides:
      clients_keystone:
        endpoint_type: publicURL
        auth_uri: "{{ keystone_service_publicurl }}"
