.. Copyright (C) 2019-2021 Maciej Delmanowski <drybjed@gmail.com>
.. Copyright (C) 2019-2021 DebOps <https://debops.org/>
.. SPDX-License-Identifier: GPL-3.0-only

Getting started
===============

.. only:: html

   .. contents::
      :local:

.. include:: ../../../includes/global.rst


Default remote keyserver
------------------------

By default the :ref:`debops.keyring` role uses the `Ubuntu keyserver`__ to
retrieve the GPG keys based on their fingerprints. The default keyserver is
configured using the :envvar:`keyring__keyserver` variable. For increased
security, or if your infrastructure is located behind a firewall that blocks
connections to the OpenPGP keyserver, you can use the ``debops.sks`` Ansible
role to set up a local instance of a SKS keyserver and import the GPG keys to
it for easy retrieval.

Previously used `SKS Keyserver pool`__ has been deprecated and won't be
maintained anymore. Thanks to the maintainers for years of great service!

.. __: https://keyserver.ubuntu.com/
.. __: https://sks-keyservers.net/


Local key store on the Ansible Controller
-----------------------------------------

The role supports usage of a local key store on the Ansible Controller, by
setting the absolute path to a directory with the GPG key files in the
:envvar:`keyring__local_path` variable. For example, to store the GPG keys
inside of the DebOps project directory, :file:`ansible/keyring/` subdirectory,
users can define in the :file:`ansible/inventory/group_vars/debops_all_hosts/keyring.yml`
file:

.. code-block:: yaml

   keyring__local_path: '{{ inventory_dir | realpath + "/../keyring" }}'

This will tell the role to look for the key files in a :file:`ansible/keyring/`
directory, relative to the Ansible inventory.

Each key file in the directory should be an ASCII-armored file, named using
a specific format:

.. code-block:: none

   0xFINGERPRINT.asc

At runtime the role will check the specified directory for any GPG key files
and will create a list which will be used to determine if a GPG key with
a given ID is available locally. If a key is found, installation from the local
key store will take precedence over other network-based methods.


Example inventory
-----------------

The role is included by default in the ``bootstrap-ldap.yml`` and the
``common.yml`` playbook, therefore you don't need to do anything to enable it.


Example playbook
----------------

If you are using this role without DebOps, here's an example Ansible playbook
that uses the ``debops.keyring`` role:

.. literalinclude:: ../../../../ansible/playbooks/service/keyring.yml
   :language: yaml
   :lines: 1,5-


Ansible tags
------------

You can use Ansible ``--tags`` or ``--skip-tags`` parameters to limit what
tasks are performed during Ansible run. This can be used after a host was first
configured to speed up playbook execution, when you are sure that most of the
configuration is already in the desired state.

Available role tags:

``role::keyring``
  Main role tag, should be used in the playbook to execute all of the role
  tasks as well as role dependencies.


Other resources
---------------

List of other useful resources related to the ``debops.keyring`` Ansible role:

- Manual pages: :man:`apt-secure(8)`, :man:`apt-key(8)`, :man:`gpg(1)`

- `SecureApt`__ page on Debian Wiki

  .. __: https://wiki.debian.org/SecureApt

- Documentation of the `Ansible ansible.builtin.apt_key module`_
