===========================================
systemd_networkd role for OpenStack-Ansible
===========================================

:tags: openstack, systemd_networkd, cloud, ansible
:category: \*nix

This role will configure Systemd units:

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

This role supports one tag: ``systemd-init``.
