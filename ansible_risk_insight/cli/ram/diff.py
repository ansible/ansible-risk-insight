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
from ...utils import show_diffs


class RAMDiffCLI:
    args = None

    def __init__(self):
        parser = argparse.ArgumentParser(description="TODO")
        parser.add_argument("target_type", help="content type", choices={"ram"})
        parser.add_argument("action", help="action for RAM command or target_name of search action")
        parser.add_argument("target_name", help="target_name for the action")
        parser.add_argument("version1", help="version string of the target")
        parser.add_argument("version2", help="version string compared")
        args = parser.parse_args()
        self.args = args

    def run(self):
        args = self.args
        action = args.action
        if action != "diff":
            raise ValueError('RAMDiffCLI cannot be executed without "diff" action')

        ram_client = RAMClient(root_dir=config.data_dir)
        diffs = ram_client.diff(args.target_name, args.version1, args.version2)
        show_diffs(diffs)
