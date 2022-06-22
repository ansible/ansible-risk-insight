==============================================
Configuring the Telemetry (ceilometer) service
==============================================

The Telemetry module (ceilometer) performs the following functions:

  - Efficiently polls metering data related to OpenStack services.

  - Collects event and metering data by monitoring notifications sent from
    services.

  - Publishes collected data to various targets including data stores and
    message queues.

.. note::

   As of Liberty, the alarming functionality is in a separate component.
   The metering-alarm containers handle the functionality through aodh
   services. For configuring these services, see the aodh docs:
   https://docs.openstack.org/aodh/latest/

Configuring the hosts
~~~~~~~~~~~~~~~~~~~~~

Configure ceilometer by specifying the ``metering-compute_hosts`` and
``metering-infra_hosts`` directives in the
``/etc/openstack_deploy/conf.d/ceilometer.yml`` file:
`ceilometer.yml.example
<https://opendev.org/openstack/openstack-ansible/tree/etc/openstack_deploy/conf.d/ceilometer.yml.example>`_

The ``metering-compute_hosts`` host the ``ceilometer-agent-compute``
service. It runs on each compute node and polls for resource
utilization statistics. The ``metering-infra_hosts`` host several
services:

  - A central agent (ceilometer-agent-central): Runs on a central
    management server to poll for resource utilization statistics for
    resources not tied to instances or compute nodes. Multiple agents
    can be started to enable workload partitioning (See HA section
    below).

  - A notification agent (ceilometer-agent-notification): Runs on a
    central management server(s) and consumes messages from the
    message queue(s) to build event and metering data, then sends it
    to one or more publishers. Multiple notification agents can be
    started to enable workload partitioning (See HA section below).

  - An API server (ceilometer-api): Runs on one or more central
    management servers to provide data access from the data store.


Configuring the hosts for an HA deployment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Ceilometer supports running the polling and notification agents in an
HA deployment.

The Tooz library provides the coordination within the groups of service
instances. Tooz can be used with several backends. At the time of this
writing, the following backends are supported:

  - Zookeeper: Recommended solution by the Tooz project.

  - Redis: Recommended solution by the Tooz project.

  - Memcached: Recommended for testing.

.. important::

   The OpenStack-Ansible project does not deploy these backends.
   One of the backends must exist before deploying the ceilometer service.

Achieve HA by configuring the proper directives in ``ceilometer.conf`` using
``ceilometer_ceilometer_conf_overrides`` in the ``user_variables.yml`` file.
The `Ceilometer Admin Guide`_ details the
options used in ``ceilometer.conf`` for HA deployment. The following is an
example of ``ceilometer_ceilometer_conf_overrides``:

.. _Ceilometer Admin Guide: https://docs.openstack.org/admin-guide/telemetry-data-collection.html

.. code-block:: yaml

   ceilometer_ceilometer_conf_overrides:
     coordination:
       backend_url: "zookeeper://172.20.1.110:2181"
     notification:
       workload_partitioning: True
