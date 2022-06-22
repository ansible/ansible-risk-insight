#!/usr/bin/env bash
# Copyright 2016, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
set -e

# Execution example: lxc-veth-wiring.sh testing VETHTEST eth1 br-mgmt

# CLI variables
CONTAINER_NAME="${1}"
export CPID=$(lxc-info -Hpn ${CONTAINER_NAME});
VETH="${2}"
INTERFACE="${3}"
BRIDGE="${4}"
VETH_PEER="$(openssl rand -hex 4)"
BRIDGE_TYPE="${5}"

# PID of running container
PID="$(lxc-info -pHn ${CONTAINER_NAME})"

# Exit 0 means no change, exit 3 is changed, any other exit is fail.
EXIT_CODE=0

function ns_cmd {
  nsenter --mount=/proc/$CPID/ns/mnt \
          --net=/proc/$CPID/ns/net \
          --pid=/proc/$CPID/ns/pid \
          --uts=/proc/$CPID/ns/uts \
          --ipc=/proc/$CPID/ns/ipc -- $@
}

if ! ip a l "${VETH}";then
  ip link add name "${VETH}" type veth peer name "${VETH_PEER}"
  EXIT_CODE=3
fi

ip link set dev "${VETH}" up

if ip a l "${VETH_PEER}";then
  ip link set dev "${VETH_PEER}" up
  ip link set dev "${VETH_PEER}" netns "${PID}" name "${INTERFACE}"
  EXIT=3
fi

if [ "${BRIDGE}" !=  "openvswitch" ]; then
  if ! brctl show "${BRIDGE}" | grep -q "${VETH}"; then
    brctl addif "${BRIDGE}" "${VETH}"
    EXIT_CODE=3
  fi
fi

ns_cmd ip link set dev "${INTERFACE}" down || true
ns_cmd systemctl restart systemd-networkd

# Sleep for 2s to avoid more than 5 restarts of systemd-networkd in
# 10s. Otherwise the systemd service restart limit will be reached
# and the service will fail to restart.
sleep 2

exit ${EXIT_CODE}
