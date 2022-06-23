Curator
=======

A role to install Curator which can delete Elasticsearch indices on a timed basis.

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
         - curator
