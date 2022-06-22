========
Overview
========

.. include:: ../../README.rst


`Tempest <https://docs.openstack.org/tempest/latest/>`_ is a testing
framework consisting of a set of integration tests to test any deployed
OpenStack cloud.


os_tempest mission
------------------

To provide a re-usable ansible role which installs, configures and runs
Tempest.


Why?
----

The reason we have come up with this idea is because every OpenStack
project uses playbooks and shell scripts to install, run and configure Tempest
which are only slightly different but their purpose is the same.

When every project uses its own way to use Tempest, it's really harder to
cooperate (cross projects) together to solve any issues which may occur.

That's where the re-usability steps in. By using the same role we can faster
react to any issues which occurred in one project and may have an effect on
another one.


Advantages
----------

* maintenance of only one set of playbooks and scripts
* heads-up for issues related to particular tests
* bigger focus on development and maintenance of the one set of playbooks and
  scripts
* decreasing of time consumption needed to install, configure and run Tempest
  for new OpenStack projects - no need to write their CI Tempest procedures
  from scratch
