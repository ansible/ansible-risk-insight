========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/openstack-ansible-os_gnocchi.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

=========================
OpenStack-Ansible Gnocchi
=========================

Ansible role which installs and configures OpenStack Gnocchi. Gnocchi installs
behind an Apache webserver listening for HTTP connections on port 8041 and
writes to filesystem storage by default.

The role can readily be configured to use Swift or Ceph storage as desired and
may be used as a stand-alone service integrated with Keystone for auth or with
Ceilometer as a metrics source.

Documentation for the project can be found at:
  https://docs.openstack.org/openstack-ansible-os_gnocchi/latest/

Release notes for the project can be found at:
  https://docs.openstack.org/releasenotes/openstack-ansible-os_gnocchi/

The project source code repository is located at:
  https://opendev.org/openstack/openstack-ansible-os_gnocchi/

The project home is at:
  https://launchpad.net/openstack-ansible

The bugs can be found at:
  https://bugs.launchpad.net/openstack-ansible
