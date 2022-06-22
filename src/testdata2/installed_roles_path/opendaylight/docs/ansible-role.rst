Ansible Role
============
Ansible role for the `OpenDaylight SDN controller`_.

Installing Ansible-OpenDaylight
-------------------------------
The Ansible Galaxy tool that ships with Ansible can be used to install
ansible-opendaylight.

To install the latest version of Ansible on Red Hat-based OSs:

::

    $ sudo yum install -y ansible


To install the latest version of Ansible on Debian-based OSs:

::

    $ sudo apt-add-repository ppa:ansible/ansible
    $ sudo apt-get update
    $ sudo apt-get install -y ansible


After you install **ansible-galaxy**, install ansible-opendaylight:

::

    $ ansible-galaxy install git+ssh://<LF ID>@git.opendaylight.org:29418/integration/packaging/ansible-opendaylight.git

The OpenDaylight Ansible role doesn't depend on any other Ansible roles.

Role Variables
--------------

Karaf Features
^^^^^^^^^^^^^^
To set extra Karaf features to be installed at OpenDaylight start time, pass
them in a list to the **extra_features** variable. The extra features you pass
will typically be driven by the requirements of your use case.

OpenDaylight normally installs a default set of Karaf features at boot. They
are recommended, so the ODL Ansible role defaults to installing them. This can
be customized by overriding the **default_features** variable. You shouldn't
normally need to do so.

REST API Port
^^^^^^^^^^^^^
To change OpenDaylight's northbound REST API port from the default of 8181, use
the **odl_rest_port** variable.

For example, in an Openstack deployment, the Swift project uses 8181 and
conflicts with OpenDaylight.

The Ansible role will handle opening this port in FirewallD if it's active.

Install Method
^^^^^^^^^^^^^^
OpenDaylight supports RPM and deb-based installs, either from a repository
or directly from a URL to a package. Use the **instal_method** var to configure
which deployment scenario is used.

Valid options:
  rpm_repo: Install ODL using its Yum repo config
  rpm_path: Install ODL RPM from a local path or remote URL
  dep_repo: Install ODL using a Debian repository
  deb_path: Install ODL .deb from a local path or remote URL

Installing OpenDaylight
-----------------------
To install OpenDaylight via ansible-opendaylight, use **ansible-playbook**.

::

    sudo ansible-playbook -i "localhost," -c local examples/<playbook>

Example playbooks are provided for various deployments.

Example Playbooks
-----------------
The playbook below would install and configure OpenDaylight using all defaults.

::

    ---
    - hosts: example_host
        sudo: yes
    roles:
        - opendaylight

To override default settings, pass variables to the **opendaylight** role.

::

    ---
    - hosts: all
      sudo: yes
      roles:
        - role: opendaylight
          extra_features: ['odl-netvirt-openstack']

Results in:

::

    opendaylight-user@root>feature:list | grep odl-netvirt-openstack
    odl-netvirt-openstack | <odl-release> | x | odl-netvirt-<odl-release> | OpenDaylight :: NetVirt :: OpenStack

License
-------
OpenDaylight is Open Source. Contributions encouraged!

Author Information
------------------
The `OpenDaylight Integration/Packaging project`_ maintains this role.

.. _OpenDaylight SDN controller: https://www.opendaylight.org/what-we-do/odl-platform-overview
.. _OpenDaylight Integration/Packaging project: https://wiki.opendaylight.org/view/Integration/Packaging