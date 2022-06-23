Ocim appserver role
===================

This role is meant to run on Ocim app servers before the main Open edX playbook.  It currently sets
up Consul Connect proxies for connecting to Redis and memcached.

Role Variables
--------------

The only required variable is `ansible_instance_id`, which is used to derive the Consul service
names to connect to.
