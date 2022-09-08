.. Copyright (C) 2014-2016 Nick Janetakis <nick.janetakis@gmail.com>
.. Copyright (C) 2014-2017 Maciej Delmanowski <drybjed@gmail.com>
.. Copyright (C) 2016      Reto Gantenbein <reto.gantenbein@linuxmonk.ch>
.. Copyright (C) 2014-2017 DebOps <https://debops.org/>
.. SPDX-License-Identifier: GPL-3.0-only

Description
===========

`Elasticsearch <https://en.wikipedia.org/wiki/Elasticsearch>`_ is a distributed
search engine and storage system, also a part of the Elastic Stack.
The software is developed by `Elastic <https://www.elastic.co/>`_.

The ``debops.elasticsearch`` Ansible role can be used to deploy and manage
Elasticsearch instances on one or more (3+) hosts. The role can be used as
a dependency by other Ansible roles to allow control over their configuration
options in the Elasticsearch configuration file.
