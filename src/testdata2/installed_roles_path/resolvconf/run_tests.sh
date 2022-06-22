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

set -euov

FUNCTIONAL_TEST=${FUNCTIONAL_TEST:-true}

# prep the host
if [ "$(which apt-get)" ]; then
  apt-get update && apt-get install -y build-essential python2.7 python-dev git-core libffi-dev libssl-dev
fi

if [ "$(which yum)" ]; then
  yum install -y '@Development Tools' python-devel git libffi-devel openssl-devel
fi

# get pip, if necessary
if [ ! "$(which pip)" ]; then
  curl --silent --show-error --retry 5 \
    https://bootstrap.pypa.io/get-pip.py | sudo python2.7
fi

# install tox
pip install tox

# run through each tox env and execute the test
for tox_env in $(awk -F= '/envlist/ {print $2}' tox.ini | sed 's/,/ /g'); do
  if [ "${tox_env}" != "functional" ]; then
    tox -e ${tox_env}
  elif [ "${tox_env}" == "functional" ]; then
    if ${FUNCTIONAL_TEST}; then
      tox -e ${tox_env}
    fi
  fi
done
