redis-exporter
==============

Extends [prometheus_redis_exporter_role](https://github.com/idealista/prometheus_redis_exporter_role)
to expose the size of the specified Redis key.

Role Variables
--------------

Check available variables here:
- `playbooks/roles/prometheus_redis_exporter_role/defaults/main.yml`
- `playbooks/roles/redis-exporter/defaults/main.yml`

Dependencies
------------

- nginx-proxy
- [prometheus_redis_exporter_role](https://github.com/idealista/prometheus_redis_exporter_role)
