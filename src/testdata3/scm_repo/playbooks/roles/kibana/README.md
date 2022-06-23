Kibana
======

A role to install Kibana which allows us to view logs stored in Elasticsearch.

Important Note
--------------
To enable the Kibana Alerting System, the communication between Kibana and Elasticsearch had to be over SSL, and x-pack security needed to be turned on. To know more about different configurations in ``kibana.yml`` check Kibana Documentation here - https://www.elastic.co/guide/en/kibana/7.x/alert-action-settings-kb.html.

If ELK stack already installed in the server and running this has an issue with Kibana not being able to connect with Elasticsearch then check README on the ``elasticsearch`` Role. You might need to set up the Kibana user's password manually.

Requirements
------------

N/A

Role Variables
--------------

See `defaults/main.yml`.

Dependencies
------------

See `meta/main.yml`.

Example Playbook
----------------

    - hosts: all
      roles:
         - kibana
