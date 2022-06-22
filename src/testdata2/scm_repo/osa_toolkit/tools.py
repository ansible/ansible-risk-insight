#!/usr/bin/env python
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
#
# (c) 2016, Nolan Brubaker <nolan.brubaker@rackspace.com>
import glob
import os
from os import path
import yaml

CONFIGS_DIR = path.join(os.getcwd(), 'etc', 'openstack_deploy')
AIO_CONFIG_FILE = path.join(CONFIGS_DIR, 'openstack_user_config.yml.aio')
CONFD = path.join(CONFIGS_DIR, 'conf.d')


def make_example_config(aio_config_file, configs_dir):
    """Build an inventory configuration based on example AIO files

    :param aio_config_file: ``str`` Master AIO configuration example file
    :param configs_dir: ``str`` Directory containing independent conf.d files
    """
    config = {}

    files = glob.glob(os.path.join(configs_dir, '*.aio'))
    for file_name in files:
        with open(file_name, 'r') as f:
            config.update(yaml.safe_load(f.read()))

    with open(aio_config_file, 'r') as f:
        config.update(yaml.safe_load(f.read()))

    return config


def write_example_config(filename, config):
    """Dump generated configuration to a file.

    :param filename: ``str`` The filename which to write to.
    :param config: ``dict`` Dictionary containing the config which to write.
    """
    with open(os.path.realpath(filename), 'w') as f:
        f.write(yaml.dump(config, default_flow_style=False))
