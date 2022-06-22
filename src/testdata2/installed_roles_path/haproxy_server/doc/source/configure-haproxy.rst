==============================
Configuring HAProxy (optional)
==============================

HAProxy provides load balancing services and SSL termination when hardware
load balancers are not available for high availability architectures deployed
by OpenStack-Ansible. The default HAProxy configuration provides highly-
available load balancing services via keepalived if there is more than one
host in the ``haproxy_hosts`` group.

.. important::

  Ensure you review the services exposed by HAProxy and limit access
  to these services to trusted users and networks only. For more details,
  refer to the :dev_docs:`Securing network access to OpenStack services <reference/architecture/security.html#securing-network-access-to-openstack-services>` section.

.. note::

  For a successful installation, you require a load balancer. You may
  prefer to make use of hardware load balancers instead of HAProxy. If hardware
  load balancers are in use, then implement the load balancing configuration for
  services prior to executing the deployment.

To deploy HAProxy within your OpenStack-Ansible environment, define target
hosts to run HAProxy:

   .. code-block:: yaml

       haproxy_hosts:
         infra1:
           ip: 172.29.236.101
         infra2:
           ip: 172.29.236.102
         infra3:
           ip: 172.29.236.103

There is an example configuration file already provided in
``/etc/openstack_deploy/conf.d/haproxy.yml.example``. Rename the file to
``haproxy.yml`` and configure it with the correct target hosts to use HAProxy
in an OpenStack-Ansible deployment.

Making HAProxy highly-available
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If multiple hosts are found in the inventory, deploy
HAProxy in a highly-available manner by installing keepalived.

To make keepalived work, edit at least the following variables
in ``user_variables.yml``:

.. code-block:: yaml

   haproxy_keepalived_external_vip_cidr: 192.168.0.4/25
   haproxy_keepalived_internal_vip_cidr: 172.29.236.54/16
   haproxy_keepalived_external_interface: br-flat
   haproxy_keepalived_internal_interface: br-mgmt

- ``haproxy_keepalived_internal_interface`` and
  ``haproxy_keepalived_external_interface`` represent the interfaces on the
  deployed node where the keepalived nodes bind the internal and external
  vip. By default, use ``br-mgmt``.

- On the interface listed above, ``haproxy_keepalived_internal_vip_cidr`` and
  ``haproxy_keepalived_external_vip_cidr`` represent the internal and
  external (respectively) vips (with their prefix length).

- Set additional variables to adapt keepalived in your deployment.
  Refer to the ``user_variables.yml`` for more descriptions.

To always deploy (or upgrade to) the latest stable version of keepalived.
Edit the ``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

   keepalived_use_latest_stable: True

The HAProxy nodes have group vars applied that define the configuration
of keepalived. This configuration is stored in
``group_vars/haproxy_all/keepalived.yml``. It contains the variables
needed for the keepalived role (master and backup nodes).

Keepalived pings a public and private IP address to check its status. The
default address is ``193.0.14.129``. To change this default,
set the ``keepalived_external_ping_address`` and
``keepalived_internal_ping_address`` variables in the
``user_variables.yml`` file.

.. note::

   The keepalived test works with IPv4 addresses only.

You can adapt keepalived to your environment by either using our override
mechanisms (per host with userspace ``host_vars``, per group with
userspace``group_vars``, or globally using the userspace
``user_variables.yml`` file)

If you wish to deploy multiple haproxy hosts without keepalived and
provide your own means for failover between them, edit
``/etc/openstack_deploy/user_variables.yml`` to skip the deployment
of keepalived.
To do this, set the following:

.. code-block:: yaml

   haproxy_use_keepalived: False



Configuring keepalived ping checks
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

OpenStack-Ansible configures keepalived with a check script that pings an
external resource and uses that ping to determine if a node has lost network
connectivity. If the pings fail, keepalived fails over to another node and
HAProxy serves requests there.

The destination address, ping count and ping interval are configurable via
Ansible variables in ``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

   keepalived_external_ping_address:   # Public IP address to ping
   keepalived_internal_ping_address:   # Private IP address to ping
   keepalived_ping_count:              # ICMP packets to send (per interval)
   keepalived_ping_interval:           # How often ICMP packets are sent

By default, OpenStack-Ansible configures keepalived to ping one of the root
DNS servers operated by RIPE. You can change this IP address to a different
external address or another address on your internal network.

If external connectivity fails, it is important that internal services can
still access an HAProxy instance. In a situation, when ping to some external
host fails and internal ping is not separated, all keepalived instances enter
the fault state despite internal connectivity being still available. Separate
ping check for internal and external connectivity ensures that when one
instance fails the other VIP remains in operation.

Securing HAProxy communication with SSL certificates
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The OpenStack-Ansible project provides the ability to secure HAProxy
communications with self-signed or user-provided SSL certificates. By default,
self-signed certificates are used with HAProxy. However, you can
provide your own certificates by using the following Ansible variables:

.. code-block:: yaml

    haproxy_user_ssl_cert:          # Path to certificate
    haproxy_user_ssl_key:           # Path to private key
    haproxy_user_ssl_ca_cert:       # Path to CA certificate

Refer to `Securing services with SSL certificates`_ for more information on
these configuration options and how you can provide your own
certificates and keys to use with HAProxy. User provided certificates should
be folded and formatted at 64 characters long. Single line certificates
will not be accepted by HAProxy and will result in SSL validation failures.
Please have a look here for information on `converting your certificate to
various formats <https://search.thawte.com/support/ssl-digital-certificates/index?page=content&actp=CROSSLINK&id=SO26449>`_.

Using Certificates from LetsEncrypt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you want to use `LetsEncrypt SSL Service <https://letsencrypt.org/>`_
you can activate the feature by providing the following configuration in
``/etc/openstack_deploy/user_variables.yml``. Note that this requires
that ``external_lb_vip_address`` in
``/etc/openstack_deploy/openstack_user_config.yml`` is set to the
external DNS address.

The following variables must be set for the haproxy hosts.

.. code-block:: yaml

   haproxy_ssl_letsencrypt_enable: True
   haproxy_ssl_letsencrypt_install_method: "distro"
   haproxy_ssl_letsencrypt_email: example@example.com
   haproxy_interval: 2000

The following variables serve as an example for how to configure a
single HAProxy providing SSL termination for a service on the same
host, served from 127.0.0.1:80. An additional HAProxy backend is
configured which will receive the acme-challenge requests when
certificates are renewed.

.. code-block:: yaml

  haproxy_service_configs:
    # the external facing service which serves the apache test site, with a acl for LE requests
    - service:
        haproxy_service_name: test
        haproxy_redirect_http_port: 80                         #redirect port 80 to port ssl
        haproxy_redirect_scheme: "https if !{ ssl_fc } !{ path_beg /.well-known/acme-challenge/ }"   #redirect all non-ssl traffic to ssl except acme-challenge
        haproxy_port: 443
        haproxy_frontend_acls:                                 #use a frontend ACL specify the backend to use for acme-challenge
          letsencrypt-acl:
              rule: "path_beg /.well-known/acme-challenge/"
              backend_name: letsencrypt
        haproxy_ssl: True
        haproxy_backend_nodes:                                 #apache is running on locally on 127.0.0.1:80 serving a dummy site
          - name: local-test-service
            ip_addr: 127.0.0.1
        haproxy_balance_type: http
        haproxy_backend_port: 80
        haproxy_backend_options:
          - "httpchk HEAD /"                                   # request to use for health check for the example service

    # an internal only service for acme-challenge whose backend is certbot on the haproxy host
    - service:
        haproxy_service_name: letsencrypt
        haproxy_backend_nodes:
          - name: localhost
            ip_addr: {{ ansible_host }}                        #certbot binds to the internal IP
        backend_rise: 1                                        #quick rise and fall time for multinode deployment to succeed
        backend_fall: 2
        haproxy_bind:
          - 127.0.0.1                                          #bind to 127.0.0.1 as the local internal address  will be used by certbot
        haproxy_port: 8888                                     #certbot is configured with http-01-port to be 8888
        haproxy_balance_type: http


It is possible to use an HA configuration of HAProxy with certificates
initialised and renewed using certbot by setting haproxy_backend_nodes
for the LetsEncrypt service to include all HAProxy internal addresses.
Each HAProxy instance will be checking for certbot running on its own
node plus each of the others, and direct any incoming acme-challenge
requests to the HAProxy instance which is performing a renewal.

It is necessary to configure certbot to bind to the HAproxy node local
internal IP address via the haproxy_ssl_letsencrypt_certbot_bind_address
variable in a H/A setup.

Using Certificates from LetsEncrypt (legacy method)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


If you want to use `LetsEncrypt SSL Service <https://letsencrypt.org/>`_
you can activate the feature by providing the following configuration in
``/etc/openstack_deploy/user_variables.yml``. Note that this requires
that ``external_lb_vip_address`` in
``/etc/openstack_deploy/openstack_user_config.yml`` is set to the
external DNS address.

.. code-block:: yaml

   haproxy_ssl_letsencrypt_enable: true
   haproxy_ssl_letsencrypt_email: example@example.com

.. warning::

   There is no certificate distribution implementation at this time, so
   this will only work for a single haproxy-server environment.  The
   renewal is automatically handled via CRON and currently will shut
   down haproxy briefly during the certificate renewal.  The
   haproxy shutdown/restart will result in a brief service interruption.

.. _Securing services with SSL certificates: https://docs.openstack.org/project-deploy-guide/openstack-ansible/draft/app-advanced-config-sslcertificates.html

Configuring additional services
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Additional haproxy service entries can be configured by setting
``haproxy_extra_services`` in ``/etc/openstack_deploy/user_variables.yml``

For more information on the service dict syntax, please reference
``playbooks/vars/configs/haproxy_config.yml``

An example HTTP service could look like:

.. code-block:: yaml

    haproxy_extra_services:
      - service:
          haproxy_service_name: extra-web-service
          haproxy_backend_nodes: "{{ groups['service_group'] | default([]) }}"
          haproxy_ssl: "{{ haproxy_ssl }}"
          haproxy_port: 10000
          haproxy_balance_type: http
          # If backend connections should be secured with SSL (default False)
          haproxy_backend_ssl: True
          haproxy_backend_ca: /path/to/ca/cert.pem
          # Or to use system CA for validation
          # haproxy_backend_ca: True
          # Or if certificate validation should be disabled
          # haproxy_backend_ca: False

Additionally, you can specify haproxy services that are not managed
in the Ansible inventory by manually specifying their hostnames/IP Addresses:

.. code-block:: yaml

    haproxy_extra_services:
      - service:
          haproxy_service_name: extra-non-inventory-service
          haproxy_backend_nodes:
            - name: nonInvHost01
              ip_addr: 172.0.1.1
            - name: nonInvHost02
              ip_addr: 172.0.1.2
            - name: nonInvHost03
              ip_addr: 172.0.1.3
          haproxy_ssl: "{{ haproxy_ssl }}"
          haproxy_port: 10001
          haproxy_balance_type: http

Adding additional global VIP addresses
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some cases, you might need to add additional internal VIP addresses
to the load balancer front end. You can use the HAProxy role to add
additional VIPs to all front ends by setting them in the
``extra_lb_vip_addresses`` or ``extra_lb_tls_vip_addresses`` variables.

The following example shows extra VIP addresses defined in the
``user_variables.yml`` file:

.. code-block:: yaml

   extra_lb_vip_addresses:
     - 10.0.0.10
     - 192.168.0.10

The following example shows extra VIP addresses with TLS enabled
defined in the ``user_variables.yml`` file:

.. code-block:: yaml

   extra_lb_tls_vip_addresses:
     - 10.0.0.10
     - 192.168.0.10

Overriding the address haproxy will bind to
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

In some cases you may want to override the default of having haproxy
bind to the addresses specified in ``external_lb_vip_address`` and
``internal_lb_vip_address``. For example if those are hostnames and you
want haproxy to bind to IP addresses while preserving the names for TLS-
certificates and endpoint URIs.

This can be set in the ``user_variables.yml`` file:

.. code-block:: yaml

   haproxy_bind_external_lb_vip_address: 10.0.0.10
   haproxy_bind_internal_lb_vip_address: 192.168.0.10

Adding Access Control Lists to HAProxy front end
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Adding ACL rules in HAProxy is easy. You just need to define haproxy_acls and
add the rules in the variable

Here is an example that shows how to achieve the goal

.. code-block:: yaml


   - service:
          haproxy_service_name: influxdb-relay
          haproxy_acls:
              write_queries:
                 rule: "path_sub -i write"
              read_queries:
                 rule: "path_sub -i query"
                 backend_name: "influxdb"

This will add two acl rules ``path_sub -i write`` and ``path_sub -i query``  to
the front end and use the backend specified in the rule. If no backend is specified
it will use a default ``haproxy_service_name`` backend.

If a frontend service directs to multiple backend services using ACLs, and a
backend service does not require its own corresponding front-end, the
`haproxy_backend_only` option can be specified:

.. code-block:: yaml

  - service:
        haproxy_service_name: influxdb
        haproxy_backend_only: true # Directed by the 'influxdb-relay' service above
        haproxy_backend_nodes:
          - name: influxdb-service
            ip_addr: 10.100.10.10

Adding prometheus metrics to haproxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Since haproxy 2.0 it's possible to exposes prometheus metrics.
https://www.haproxy.com/blog/haproxy-exposes-a-prometheus-metrics-endpoint/
if you need to create a frontend for it you can use the `haproxy_frontend_only`
option:

.. code-block:: yaml

  - service:
      haproxy_service_name: prometheus-metrics
      haproxy_port: 8404
      haproxy_bind:
        - '127.0.0.1'
      haproxy_whitelist_networks: "{{ haproxy_whitelist_networks }}"
      haproxy_frontend_only: True
      haproxy_frontend_raw:
        - 'http-request use-service prometheus-exporter if { path /metrics }'
      haproxy_service_enabled: True
      haproxy_balance_type: 'http'
