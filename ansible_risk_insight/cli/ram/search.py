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
from ...utils import split_name_and_version


class RAMSearchCLI:
    args = None

    def __init__(self):
        parser = argparse.ArgumentParser(description="TODO")
        parser.add_argument("target_type", help="content type", choices={"ram"})
        parser.add_argument("action", help="action for RAM command or target_name of search action")
        parser.add_argument("target_name", help="target_name for the action")
        args = parser.parse_args()
        self.args = args

    def run(self):
        args = self.args
        action = args.action
        target_name = args.target_name
        if action != "search":
            raise ValueError('RAMSearchCLI cannot be executed without "search" action')

        ram_client = RAMClient(root_dir=config.data_dir)

        target_name, target_version = split_name_and_version(target_name)
        findings = ram_client.search_findings(target_name, target_version)
        if findings:
            print(findings.summary_txt)
