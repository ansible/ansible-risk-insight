=====
Usage
=====


Execute by ansible-playbook
---------------------------

First you need to install ``os_tempest`` role. For more information about the
installation process refer to the `Installation`_ page.

.. _Installation: ./installation.html

After the role is installed enter the `openstack-ansible-os_tempest` directory.

First thing which needs to be done in order to execute ``os_tempest`` role
is setting a cloud name. For information on how to do that, please, have a look
at `Set the name of the cloud`_ page.

.. _Set the name of the cloud: ../configuration.html#set-the-name-of-the-cloud

An example ``playbook.yml`` can be seen below in `Example playbook`_ section.

.. _Example playbook: ./usage.html#example-playbook

After the required variables in the ``playbook.yml`` file are set you can
execute the role as follows:

.. code-block:: shell

    $ ansible-playbook playbook.yaml


Example playbook
----------------

.. literalinclude:: ../../../examples/playbook.yml
   :language: yaml


Dependencies
------------

This role requires the following packages to be installed on the target host:

- pip >= 7.1
- python-virtualenv
