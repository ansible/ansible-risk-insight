Ansible role for deploying a WSGI web application
=================================================

This role deploys a minimal Python WSGI web application using Gunicorn, Supervisor and Nginx. This is a very minimal,
WIP role which, at the moment, doesn't support installing additional dependencies, using any backend database/storage,
static files and anything else other than just installing the requirements and configuring the appserver and the web server.

The variables used by this role can be found in `defaults/main.yml` and overridden.

The `pr-watcher-notifier` role is the only consumer of this role at the moment.
