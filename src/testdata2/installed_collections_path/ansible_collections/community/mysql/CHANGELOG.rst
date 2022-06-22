========================================
Community MySQL Collection Release Notes
========================================

.. contents:: Topics

This changelog describes changes after version 2.0.0.

v3.2.1
======

Release Summary
---------------

This is the patch release of the ``community.mysql`` collection.
This changelog contains all changes to the modules in this collection
that have been added after the release of ``community.mysql`` 3.2.0.

Bugfixes
--------

- Include ``PSF-license.txt`` file for ``plugins/module_utils/_version.py``.

v3.2.0
======

Release Summary
---------------

This is the minor release of the ``community.mysql`` collection.
This changelog contains all changes to the modules in this collection
that have been added after the release of ``community.mysql`` 3.1.3.

Major Changes
-------------

- The community.mysql collection no longer supports ``Ansible 2.9`` and ``ansible-base 2.10``. While we take no active measures to prevent usage and there are no plans to introduce incompatible code to the modules, we will stop testing against ``Ansible 2.9`` and ``ansible-base 2.10``. Both will very soon be End of Life and if you are still using them, you should consider upgrading to the ``latest Ansible / ansible-core 2.11 or later`` as soon as possible (https://github.com/ansible-collections/community.mysql/pull/343).

Minor Changes
-------------

- mysql_user and mysql_role: Add the argument ``subtract_privs`` (boolean, default false, mutually exclusive with ``append_privs``). If set, the privileges given in ``priv`` are revoked and existing privileges are kept (https://github.com/ansible-collections/community.mysql/pull/333).

Bugfixes
--------

- mysql_user - fix missing dynamic privileges after revoke and grant privileges to user (https://github.com/ansible-collections/community.mysql/issues/120).
- mysql_user - fix parsing privs when a user has roles assigned (https://github.com/ansible-collections/community.mysql/issues/231).

v3.1.3
======

Release Summary
---------------

This is the patch release of the ``community.mysql`` collection.
This changelog contains all changes to the modules in this collection
that have been added after the release of ``community.mysql`` 3.1.2.

Bugfixes
--------

- mysql_replication - fails when using the `primary_use_gtid` option with `slave_pos` or `replica_pos` (https://github.com/ansible-collections/community.mysql/issues/335).
- mysql_role - remove redundant connection closing (https://github.com/ansible-collections/community.mysql/pull/330).
- mysql_user - fix the possibility for a race condition that breaks certain (circular) replication configurations when ``DROP USER`` is executed on multiple nodes in the replica set. Adding ``IF EXISTS`` avoids the need to use ``sql_log_bin: no`` making the statement always replication safe (https://github.com/ansible-collections/community.mysql/pull/287).

v3.1.2
======

Release Summary
---------------

This is the patch release of the ``community.mysql`` collection.
This changelog contains all changes to the modules in this collection
that have been added after the release of ``community.mysql`` 3.1.1.

Bugfixes
--------

- Collection core functions - fixes related to the mysqlclient Python connector (https://github.com/ansible-collections/community.mysql/issues/292).

v3.1.1
======

Release Summary
---------------

This is the patch release of the ``community.mysql`` collection.
This changelog contains all changes to the modules in this collection
that have been added after the release of ``community.mysql`` 3.1.0.

Bugfixes
--------

- mysql_role - make the ``set_default_role_all`` parameter actually working (https://github.com/ansible-collections/community.mysql/pull/282).

v3.1.0
======

Release Summary
---------------

This is the minor release of the ``community.mysql`` collection.
This changelog contains all changes to the modules in this collection
that have been added after the release of ``community.mysql`` 3.0.0.

Minor Changes
-------------

- Added explicit description of the supported versions of databases and connectors. Changes to the collection are **NOT** tested against database versions older than `mysql 5.7.31` and `mariadb 10.2.37` or connector versions older than `pymysql 0.7.10` and `mysqlclient 2.0.1`. (https://github.com/ansible-collections/community.mysql/discussions/141)
- mysql_user - added the ``force_context`` boolean option to set the default database context for the queries to be the ``mysql`` database. This way replication/binlog filters can catch the statements (https://github.com/ansible-collections/community.mysql/issues/265).

Bugfixes
--------

- Collection core functions - use vendored version of ``distutils.version`` instead of the deprecated Python standard library ``distutils`` (https://github.com/ansible-collections/community.mysql/pull/269).

v3.0.0
======

Release Summary
---------------

This is the major release of the ``community.mysql`` collection.
This changelog contains all breaking changes to the modules in this collection
that have been added after the release of ``community.mysql`` 2.3.2.

Breaking Changes / Porting Guide
--------------------------------

- mysql_replication - remove ``Is_Slave`` and ``Is_Master`` return values (were replaced with ``Is_Primary`` and ``Is_Replica`` (https://github.com/ansible-collections    /community.mysql/issues/145).
- mysql_replication - remove the mode options values containing ``master``/``slave`` and the master_use_gtid option ``slave_pos`` (were replaced with corresponding ``primary``/``replica`` values) (https://github.com/ansible-collections/community.mysql/issues/145).
- mysql_user - remove support for the `REQUIRESSL` special privilege as it has ben superseded by the `tls_requires` option (https://github.com/ansible-collections/community.mysql/discussions/121).
- mysql_user - validate privileges using database engine directly (https://github.com/ansible-collections/community.mysql/issues/234 https://github.com/ansible-collections/community.mysql/pull/243). Do not validate privileges in this module anymore.
