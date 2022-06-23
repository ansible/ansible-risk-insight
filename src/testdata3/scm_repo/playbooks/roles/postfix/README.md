Ansible role for OpenCraft's internal mail relay
================================================

This Ansible role sets up a Postfix server that accepts mail from other internal servers.  Depending
on the destination domain, the mail is either relayed to our internal incoming mail server, or to an
external service for outgoing email.

Clients connect with a TLS-encrypted connection and authenticate via SMTP authentication.  We use
Dovecot on the server as SASL authentication backend.

The Ansible variables for this role are documented in [defaults/main.yml](defaults/main.yml).
