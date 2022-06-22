===========================
OpenStack apt cache pinning
===========================

This role will set package pinning for APT packages. The role will create a
preference file used to pin packages to a *release*, *origin*, or *version*.
The pinning syntax is a simple data driven format which is a list of
dictionaries. The items must contain a *package* entry and pinning type.
Pinning types are *release*, *origin*, or *version*.

To clone or view the source code for this repository, visit the role repository
for `apt_package_pinning <https://github.com/openstack/openstack-ansible-apt_package_pinning>`_.

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
