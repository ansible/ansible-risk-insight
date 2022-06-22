============
Installation
============

This page describes how to install ``os_tempest`` role.

To clone or view the source code of ``os_tempest``, visit the role repository
for `os_tempest <https://opendev.org/openstack/openstack-ansible-os_tempest>`_.

Install dependencies via ``ansible-galaxy``:

.. code-block:: shell

    $ mkdir ~/.ansible/roles -p
    $ git clone https://opendev.org/openstack/openstack-ansible-os_tempest ~/.ansible/roles/os_tempest
    $ ansible-galaxy install -r ~/.ansible/roles/os_tempest/requirements.yml --roles-path=~/.ansible/roles/

Then you need to export a couple of variables, `ANSIBLE_ROLES_PATH` which
points to the directory where ``os_tempest`` was cloned and
`ANSIBLE_ACTION_PLUGINS` which points to the location of ``config_template``
plugin. In this case it's:

.. code-block:: shell

    $ export ANSIBLE_ROLES_PATH=$HOME/.ansible/roles
    $ export ANSIBLE_ACTION_PLUGINS=~/.ansible/roles/config_template/action

Then create a ``playbook.yaml``, you can find an `example one here`_.
Then don't forget to set the name of the cloud you're going to run the role
against, `see this page`_.

.. _example one here: ./usage.html#example-playbook
.. _see this page: ./configuration.html#set-the-name-of-the-cloud
