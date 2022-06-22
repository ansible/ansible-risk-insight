=============================
OpenStack-Ansible uWSGI role
=============================

This role installs uwsgi service either inside it's own virtualenv or
with the system python and creates systemd services based on the provided
definitions inside variable `uwsgi_services`.

To clone or view the source code for this repository, visit the role repository
for `uwsgi <https://opendev.org/openstack/ansible-role-uwsgi>`_.

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

This role supports two tags: ``uwsgi-install`` and ``uwsgi-config``.
The ``uwsgi-install`` tag can be used to install and upgrade. The
``uwsgi-config`` tag can be used to manage configuration and systemd services.
