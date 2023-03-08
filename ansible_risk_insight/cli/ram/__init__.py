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

import sys

from .search import RAMSearchCLI
from .list import RAMListCLI
from .diff import RAMDiffCLI
from .generate import RAMGenerateCLI
from .update import RAMUpdateCLI
from .release import RAMReleaseCLI


ram_actions = ["search", "list", "diff", "generate", "update", "release"]


class RAMCLI:
    _cli = None

    def __init__(self):

        args = sys.argv
        if len(args) > 2:
            action = args[2]
            # "search" can be abbreviated
            if action not in ram_actions:
                action = "search"
                target_name = sys.argv[2]
                sys.argv[2] = action
                sys.argv.insert(3, target_name)

            if action == "search":
                self._cli = RAMSearchCLI()
            elif action == "list":
                self._cli = RAMListCLI()
            elif action == "diff":
                self._cli = RAMDiffCLI()
            elif action == "generate":
                self._cli = RAMGenerateCLI()
            elif action == "update":
                self._cli = RAMUpdateCLI()
            elif action == "release":
                self._cli = RAMReleaseCLI()
            else:
                raise ValueError(f"The action {action} is not supported")
        else:
            raise ValueError(f"An action must be specified; {ram_actions}")

    def run(self):
        if self._cli:
            self._cli.run()
