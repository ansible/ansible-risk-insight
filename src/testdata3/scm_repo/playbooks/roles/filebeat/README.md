Filebeat
========

This role installs Filebeat on the server for log forwarding purposes.

You can configure the role to send any logs to any logstash endpoint.

Requirements
------------

N/A

Role Variables
--------------

See `defaults/main.yml`.

Dependencies
------------

N/A

Example Playbook
----------------

    - hosts: all
      roles:
         - filebeat
