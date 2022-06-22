#!/usr/bin/env bash

# This is a very simple script to search a host for containers that have veth pairs that are not
#  plugged into a given bridge. This can happen for a number of reasons however the most common
#  one is due to a physical network interface being bounced which severs the containers connection
#  to that interface. This script will identify container veth pairs. If any of the container veth
#  devices are missing a master the script will attempt to locate the containers network information
#  and connect the broken network link.

# Do a simple lxc command check, if the client errors assume its not installed or ready and return 0
lxc-ls --version || exit 0

# Set the default script exit status
exit_status=0
# List all containers
for container in $(lxc-ls); do
  # List Links for the containers
  for net_info in $(lxc-info -n "${container}" | awk '/Link/ {print $2}'); do
    # If the link information is a veth and does not have a "master" continue
    if ! ip -o -d link show "${net_info}" | grep veth | grep -q master; then
        # Search for the interface file that contains the veth
        lxc_interface_file=$(grep -l "\b${net_info}\b" /var/lib/lxc/${container}/{config,*.ini} | head -n 1)
        # If an interface file is found continue
        if [ ! -z "${lxc_interface_file}" ];then
            # Get the first network link line from the lxc configuration file
            veth_bridge_line=$(grep -hA10 ${net_info} "${lxc_interface_file}" | grep lxc.network.link | head -n 1)
            # If a network interface file has a link entry continue
            if [ ! -z "${veth_bridge_line}" ];then
                # get the link name
                veth_bridge=$(echo "${veth_bridge_line}" | awk -F'=' '{print $2}' | sed 's/\s//g')
                # Plug the veth into the link
                ip link set "${net_info}" master "${veth_bridge}"
                echo "container ${container} had a broken veth ${net_info} not being plugged into "${veth_bridge}": this issue is now resolved"
            else
                # Notify the user that the issues can not be automatically fixed for a given container and veth
                echo "container ${container} has a broken veth ${net_info} and an automated fix can not be found"
                # Because of the inability to resolve the issue automatically set the exit_status to failure
                exit_status=99
            fi
        fi
    fi
  done
done
exit "$exit_status"
