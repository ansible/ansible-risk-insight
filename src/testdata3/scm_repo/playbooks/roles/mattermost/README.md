Ansible role for OpenCraft's internal Mattermost chat server
============================================================

This role sets up a Mattermost server.  The service is run behind nginx, and
certbot is used to manage SSL certificates.  Email is sent to localhost, so a
local mail transport agent needs to be configured by a different role, e.g. the
[forward-server-mail][1] role.

The Ansible variables for this role are documented in [defaults/main.yml][2].

[1]: https://github.com/open-craft/ansible-forward-server-mail
[2]: defaults/main.yml
