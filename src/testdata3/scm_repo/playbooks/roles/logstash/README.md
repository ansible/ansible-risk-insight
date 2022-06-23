Logstash
========

A role to install and configure a TLS-enabled Logstash service.

Expects input beats to provide TLS details from a common certificate authority.

Important
---------
As x-pack security has been enabled, there are some extra steps that need to be taken in order to Logstash work correctly with Elasticsearch.

First, check that the user specified in the ``logstash_elasticsearch_user`` variable actually exists. To check that login to Kibana web with a superuser and go to ``Stack Management`` -> ``Users`` and check that the user exists in the list.

If it's not there, create the user with the password specified in the ``logstash_elasticsearch_password`` user. You need to set up proper permission for that user. To know more about creating a role with proper permission refer to the doc here - https://www.elastic.co/guide/en/logstash/current/ls-security.html#ls-http-auth-basic.

Create & set the ``logstash_writer`` role for that user. Logstash should work with Elasticsearch now.

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
         - logstash
