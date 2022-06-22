===========================================================
Configuring the Data Processing (sahara) service (optional)
===========================================================

.. note::

   This feature is experimental at this time and it has not been fully
   production tested yet.

Sahara provide users with a simple means to provision data processing
frameworks (such as Hadoop, Spark and Storm) on OpenStack.

Sahara is configured using the ``/etc/openstack_deploy/conf.d/sahara.yml``
file and the ``/etc/openstack_deploy/user_variables.yml`` file.

Configuring target hosts
~~~~~~~~~~~~~~~~~~~~~~~~

Modify ``/etc/openstack_deploy/conf.d/sahara.yml`` by adding a list
containing the infrastructure target hosts in the sahara-infra_hosts
section:

In ``sahara.yml``:

   .. code-block:: yaml

       sahara-infra_hosts:
         infra01:
           ip: INFRA01_IP_ADDRESS
         infra02:
           ip: INFRA02_IP_ADDRESS
         infra03:
           ip: INFRA03_IP_ADDRESS

Replace ``*_IP_ADDRESS`` with the IP address of the br-mgmt container
management bridge on each target host.

This hosts will be used to deploy the containers where sahara will be
installed.

Configuring the cluster network
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Sahara is configured to use the neutron implementation of OpenStack
Networking.

Floating IP management
----------------------

By default sahara is configured to use fixed IP addresses for access. This
is controlled by the ``sahara_use_floating_ips`` variable. By changing
``sahara_use_floating_ips`` to ``True`` the user may specify a floating IP
address pool for each node group directly.

   In ``user_variables.yml``:

   .. code-block:: yaml

       sahara_use_floating_ips: False

.. warning::
    When using floating IP addresses for management **every** instance in
    the cluster must have a floating IP address, otherwise sahara will not
    be able to utilize that cluster.

When using fixed IP addresses (``sahara_use_floating_ips=False``) the user
will be able to choose the fixed IP network for all instances in a cluster.
It is important to ensure that all instances running sahara have access to
the fixed IP networks.


Object Storage access using proxy users
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default sahara is configured to use proxy users and delegated trusts
for Object Storage access. In that way, users are not required to enter
credentials for their data sources and job binaries referenced in Object
Storage. To disable this functionality change the following variable to
``False``.

   In ``user_variables.yml``:

   .. code-block:: yaml

      sahara_use_domain_for_proxy_users: True

Also, is it possible to change which roles the trust users will receive
in the proxy domain, by default it receives the ``_member_`` role.

   In ``user_variables.yml``:

   .. code-block:: yaml

      sahara_proxy_user_role_names: _member_

.. warning::
    In the context of the proxy user, any roles that are required for
    Object Storage access by the project owning the object store must
    be delegated to the proxy user for authentication to be successful.


Configuring cluster instances NTP
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default sahara will enable the NTP service on all cluster instances if
the NTP package is included in the image. The default NTP server will be
``pool.ntp.org`` this can be overridden using the
``sahara_default_ntp_server`` variable.

   In ``user_variables.yml``:

   .. code-block:: yaml

      sahara_default_ntp_server: "pool.ntp.org"


Configuring plugins
~~~~~~~~~~~~~~~~~~~

The following plugins are installed and loaded by default:

   .. code-block:: yaml

      sahara_plugin_base:
        - vanilla
        - spark
        - cdh
        - ambari

To add/remove plugins, just change the ``sahara_plugin_base`` variable
accordingly, in the ``user_variables.yml`` file.


Configuring notifications
~~~~~~~~~~~~~~~~~~~~~~~~~

Sahara can be configured to send notifications to the OpenStack Telemetry
module. By default, the variable is set to true if there are any Ceilometer
hosts in the environment. To change this, the following variable must be
set:

   In ``user_variables.yml``:

   .. code-block:: yaml

      sahara_ceilometer_enabled: True


Dashboard
~~~~~~~~~

To enable the Data Processing panel on horizon, the following variable
should be set:

   In ``user_variables.yml``:

   .. code-block:: yaml

      horizon_enable_sahara_ui: True


Setting up Sahara
~~~~~~~~~~~~~~~~~

Run the setup-hosts playbook, to create the sahara containers, and the
repo-build playbook to update the repository with the sahara packages.

   .. code-block:: console

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible setup-hosts.yml
       # openstack-ansible repo-build.yml

Run the sahara and horizon playbooks to install sahara and enable the
Data Processing panel in horizon:

   .. code-block:: console

       # cd /opt/openstack-ansible/playbooks
       # openstack-ansible os-sahara-install.yml
       # openstack-ansible os-horizon-install.yml
