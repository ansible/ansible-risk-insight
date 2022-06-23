#!/bin/sh
#
# This file is based on /etc/cron.daily/chkrootkit provided by the distro.
#
CF=/etc/chkrootkit.conf
LOG_DIR=/var/log/chkrootkit

. $CF

echo "Updating chkrootkit expected output..."
/usr/sbin/chkrootkit $RUN_DAILY_OPTS > $LOG_DIR/log.today.raw 2>&1

# the sed expression replaces the messages about /sbin/dhclient3 /usr/sbin/dhcpd3
# with a message that is the same whatever order eth0 and eth1 were scanned
sed -r -e 's,eth(0|1)(:[0-9])?: PACKET SNIFFER\((/sbin/dhclient3|/usr/sbin/dhcpd3)\[[0-9]+\]\),eth\[0|1\]: PACKET SNIFFER\([dhclient3|dhcpd3]{PID}\),' \
-e 's/(! \w+\s+)[ 0-9]{4}[0-9]/\1#####/' $LOG_DIR/log.today.raw > $LOG_DIR/log.expected
