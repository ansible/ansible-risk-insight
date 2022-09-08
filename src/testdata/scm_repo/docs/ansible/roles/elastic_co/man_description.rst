.. Copyright (C) 2017 Maciej Delmanowski <drybjed@gmail.com>
.. Copyright (C) 2017 DebOps <https://debops.org/>
.. SPDX-License-Identifier: GPL-3.0-only

Description
===========

The ``debops.elastic_co`` Ansible role can be used to configure APT
repositories maintained by the `Elastic <https://www.elastic.co/about>`_
company on Debian and Ubuntu hosts. The APT repositories are used to distribute
``elasticsearch``, ``logstash``, ``kibana``, ``filebeat``, ``metricbeat``,
``packetbeat`` and ``heartbeat`` APT packages. The role allows only for
installation of packages, additional configuration and management of the
installed software is performed by other Ansible roles.
