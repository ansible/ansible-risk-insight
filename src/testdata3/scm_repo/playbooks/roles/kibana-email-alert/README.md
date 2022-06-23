Kibana Email Alert
==================

This role installs a service that watches journald for kibana log and if matches with defined pattern, then sends an email
alert to specified email address.

Role Variables
--------------
kibana_email_alert_regex - what to match in journald log

kibana_email_alert_to - which email to send alert

kibana_email_alert_subject - email subject

Dependencies
------------

Kibana, Journald
