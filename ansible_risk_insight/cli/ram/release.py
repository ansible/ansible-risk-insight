# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2022 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse

from ...scanner import config
from ...risk_assessment_model import RAMClient


class RAMReleaseCLI:
    args = None

    def __init__(self):
        parser = argparse.ArgumentParser(description="TODO")
        parser.add_argument("target_type", help="content type", choices={"ram"})
        parser.add_argument("action", help="action for RAM command or target_name of search action")
        parser.add_argument("-o", "--outfile", help="if execute release action, specify tar.gz file to store KB files")
        args = parser.parse_args()
        self.args = args

    def run(self):
        args = self.args
        action = args.action
        if action != "release":
            raise ValueError('RAMReleaseCLI cannot be executed without "release" action')

        if not args.outfile:
            raise ValueError(' "release" action cannot be executed without `--outfile` option. Please set "tar.gz" file name to export KB files.')

        ram_client = RAMClient(root_dir=config.data_dir)
        ram_client.release(args.outfile)
