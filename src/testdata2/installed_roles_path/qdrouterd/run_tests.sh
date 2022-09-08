#!/usr/bin/env bash
# Copyright 2015, Rackspace US, Inc.
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

# PURPOSE:
# This script clones the openstack-ansible-tests repository to the
# tests/common folder in order to be able to re-use test components
# for role testing. This is intended to be the thinnest possible
# shim for test execution outside of OpenStack CI.

# WARNING:
# This file is maintained in the openstack-ansible-tests repository.
# https://git.openstack.org/cgit/openstack/openstack-ansible-tests/tree/run_tests.sh
# If you need to modify this file, update the one in the openstack-ansible-tests
# repository and then update this file as well. The purpose of this file is to
# prepare the host and then execute all the tox tests.
#

## Shell Opts ----------------------------------------------------------------
set -xeu

## Vars ----------------------------------------------------------------------

WORKING_DIR="$(readlink -f $(dirname $0))"

COMMON_TESTS_PATH="${WORKING_DIR}/tests/common"
TESTING_HOME=${TESTING_HOME:-$HOME}
ZUUL_TESTS_CLONE_LOCATION="/home/zuul/src/git.openstack.org/openstack/openstack-ansible-tests"

# Use .gitreview as the key to determine the appropriate
# branch to clone for tests.
TESTING_BRANCH=$(awk -F'=' '/defaultbranch/ {print $2}' "${WORKING_DIR}/.gitreview")
if [[ "${TESTING_BRANCH}" == "" ]]; then
  TESTING_BRANCH="master"
fi

## Main ----------------------------------------------------------------------

# Source distribution information
source /etc/os-release || source /usr/lib/os-release

# Prefer dnf over yum for CentOS.
which dnf &>/dev/null && RHT_PKG_MGR='dnf' || RHT_PKG_MGR='yum'

# Figure out the appropriate package install command
case ${ID,,} in
    *suse*) pkg_mgr_cmd="zypper -n in" ;;
    centos|rhel|fedora) pkg_mgr_cmd="${RHT_PKG_MGR} install -y" ;;
    ubuntu|debian) pkg_mgr_cmd="apt-get install -y" ;;
    gentoo) pkg_mgr_cmd="emerge" ;;
    *) echo "unsupported distribution: ${ID,,}"; exit 1 ;;
esac

# Install git so that we can clone the tests repo if git is not available
which git &>/dev/null || eval sudo "${pkg_mgr_cmd}" git

# Clone the tests repo for access to the common test script
if [[ ! -d "${COMMON_TESTS_PATH}" ]]; then
    # The tests repo doesn't need a clone, we can just
    # symlink it.
    if [[ "$(basename ${WORKING_DIR})" == "openstack-ansible-tests" ]]; then
        ln -s "${WORKING_DIR}" "${COMMON_TESTS_PATH}"

    # In zuul v3 any dependent repository is placed into
    # /home/zuul/src/git.openstack.org, so we check to see
    # if there is a tests checkout there already. If so, we
    # symlink that and use it.
    elif [[ -d "${ZUUL_TESTS_CLONE_LOCATION}" ]]; then
        ln -s "${ZUUL_TESTS_CLONE_LOCATION}" "${COMMON_TESTS_PATH}"

    # Otherwise we're clearly not in zuul or using a previously setup
    # repo in some way, so just clone it from upstream.
    else
        git clone -b "${TESTING_BRANCH}" \
            https://git.openstack.org/openstack/openstack-ansible-tests \
            "${COMMON_TESTS_PATH}"
    fi
fi

# Execute the common test script
source tests/common/run_tests_common.sh

