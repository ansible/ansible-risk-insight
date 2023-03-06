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
from .cli import ARICLI
from .cli.ram import RAMCLI
from ansible_risk_insight.scanner import ARIScanner, Config

ari_actions = ["project", "playbook", "collection", "role", "taskfile"]
ram_actions = ["ram"]

all_actions = ari_actions + ram_actions


def main():
    if len(sys.argv) == 1:

        print("Please specify one of the following operations of ari.")
        print("[operations]")
        print("   playbook     scan a playbook (e.g. `ari playbook path/to/playbook.yml` )")
        print("   collection   scan a collection (e.g. `ari collection collection.name` )")
        print("   role         scan a role (e.g. `ari role role.name` )")
        print("   project      scan a project (e.g. `ari project path/to/project`)")
        print("   taskfile     scan a taskfile (e.g. `ari taskfile path/to/taskfile.yml`)")
        print("   ram          operate the backend data (e.g. `ari ram generate -f input.txt`)")
        sys.exit()

    action = sys.argv[1]

    if action in ari_actions:
        cli = ARICLI()
        cli.run()
    elif action == "ram":
        cli = RAMCLI()
        cli.run()
    else:
        print(f"The action {action} is not supported!", file=sys.stderr)
        sys.exit(1)


__all__ = ["ARIScanner", "Config", "models"]
