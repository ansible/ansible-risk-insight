#!/usr/bin/env bash
PATH=/usr/bin:/bin:/usr/sbin:/snap/bin
a2ensite -q 000-default.conf > /dev/null
service apache2 reload
certbot -q renew
a2dissite -q 000-default.conf > /dev/null
service apache2 reload
