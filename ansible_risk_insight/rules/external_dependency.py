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

from typing import List
from ..models import ExecutableType, TaskCall
from .base import Rule, subject_placeholder


class ExternalDependencyRule(Rule):
    name: str = "ExternalDependency"
    enabled: bool = False
    allow_list: list = []
    separate_report: bool = True
    all_ok_message = "No {} depend on external dependencies".format(subject_placeholder)

    def is_target(self, type: str, name: str) -> bool:
        return True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        collection_name = kwargs.get("collection_name", "")
        if collection_name != "":
            self.allow_list.append(collection_name)
        allow_list = kwargs.get("allow_list", [])
        if len(allow_list) > 0:
            self.allow_list.extend(allow_list)
        matched_taskcalls = []
        message = ""
        external_dependencies = []
        for taskcall in taskcalls:
            executable_type = taskcall.spec.executable_type
            if executable_type != ExecutableType.MODULE_TYPE:
                continue
            resolved_name = taskcall.spec.resolved_name
            if resolved_name == "":
                continue
            if resolved_name.startswith("ansible.builtin."):
                continue
            if "." not in resolved_name:
                continue
            parts = resolved_name.split(".")
            if len(parts) >= 2:
                collection_name = "{}.{}".format(parts[0], parts[1])
                if collection_name in self.allow_list:
                    continue
                if collection_name not in external_dependencies:
                    external_dependencies.append(collection_name)
                    matched_taskcalls.append(taskcall)
        external_dependencies = sorted(external_dependencies)

        matched = len(external_dependencies) > 0
        message = str(external_dependencies)
        return matched, matched_taskcalls, message
