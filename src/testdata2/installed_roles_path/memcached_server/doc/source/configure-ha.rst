=================================
Making Memcached highly-available
=================================

By default Memcached servers are deployed on each controller host as a part of
`shared-infra_containers` group. Drivers, like `oslo_cache.memcache_pool <https://github.com/openstack/oslo.cache/blob/master/oslo_cache/backends/memcache_pool.py>`_
support marking memcache backends as dead, however not all services allow you
to select driver which will be used for interaction with Memcached.
In the meanwhile you may face services API response delays or even unresponsive
APIs while one of the memcached backends is down.
That's why you may want to use HAProxy for handling access and check of backend
aliveness.

Configuring Memcached through HAProxy
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Setting haproxy in front of the Memcached servers and relying it in checking
aliveness of the backends gives more reliable failover and minimize delays
in case of backend failure.
We need to define the following in your ``user_variables.yml``:

.. code-block:: yaml

   haproxy_memcached_allowlist_networks: "{{ haproxy_allowlist_networks }}"
   memcached_servers: "{{ internal_lb_vip_address ~ ':' ~ memcached_port }}"
   haproxy_extra_services:
     - service:
         haproxy_service_name: memcached
         haproxy_backend_nodes: "{{ groups['memcached'] | default([]) }}"
         haproxy_bind: "{{ [internal_lb_vip_address] }}"
         haproxy_port: 11211
         haproxy_balance_type: tcp
         haproxy_balance_alg: source
         haproxy_backend_ssl: False
         haproxy_backend_options:
           - tcp-check
         haproxy_allowlist_networks: "{{ haproxy_memcached_allowlist_networks }}"

After setting that you need to update haproxy and all services configuration
to use new memcached backend:

.. code-block:: shell-session

  # openstack-ansible playbooks/haproxy-install.yml
  # openstack-ansible playbooks/setup-openstack.yml
