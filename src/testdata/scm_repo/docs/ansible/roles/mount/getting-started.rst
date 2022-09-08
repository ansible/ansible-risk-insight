.. Copyright (C) 2018 Maciej Delmanowski <drybjed@gmail.com>
.. Copyright (C) 2018 DebOps <https://debops.org/>
.. SPDX-License-Identifier: GPL-3.0-only

Getting started
===============

.. only:: html

   .. contents::
      :local:

.. include:: ../../../includes/global.rst


Example inventory
-----------------

The ``debops.mount`` role is included by default in the DebOps ``common.yml``
playbook and does not need to be explicitly enabled. It can be disabled if
needed, by setting the :envvar:`mount__enabled` boolean variable to ``False``
in the Ansible inventory.


Example playbook
----------------

If you are using this role without DebOps, here's an example Ansible playbook
that uses the ``debops.mount`` role:

.. literalinclude:: ../../../../ansible/playbooks/service/mount.yml
   :language: yaml
   :lines: 1,5-


Ansible tags
------------

You can use Ansible ``--tags`` or ``--skip-tags`` parameters to limit what
tasks are performed during Ansible run. This can be used after a host was first
configured to speed up playbook execution, when you are sure that most of the
configuration is already in the desired state.

Available role tags:

``role::mount``
  Main role tag, should be used in the playbook to execute all of the role
  tasks as well as role dependencies.


Other resources
---------------

List of other useful resources related to the ``debops.mount`` Ansible role:

- Manual pages: :man:`fstab(5)`, :man:`systemd.mount(5)`,
  :man:`systemd.automount(5)`

- `Ansible ansible.posix.mount module`_ documentation

- `Debian Wiki: fstab`__

  .. __: https://wiki.debian.org/fstab

- `Arch Linux Wiki: fstab`__

  .. __: https://wiki.archlinux.org/index.php/Fstab

- `StackExchange: What is a bind mount?`__

  .. __: https://unix.stackexchange.com/a/198591
