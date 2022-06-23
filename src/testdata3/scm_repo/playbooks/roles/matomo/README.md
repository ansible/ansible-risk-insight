Ansible role for deploying Matomo
=================================

This role deploys the [Matomo](https://matomo.org) analytics application using `docker-compose` and
sets up an SSL-terminating nginx reverse proxy in front of it.

## Variables
See `defaults/main.yml`.

## Dependencies
- `nginx-proxy` role.
