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

from dataclasses import dataclass
from ansible_risk_insight.models import (
    AnsibleRunContext,
    RunTargetType,
    ExecutableType as ActionType,
    Rule,
    Severity,
    RuleTag as Tag,
    RuleResult,
)


@dataclass
class ParameterizedImportTaskfileRule(Rule):
    rule_id: str = "R112"
    description: str = "Import/include a parameterized name of taskfile"
    enabled: bool = True
    name: str = "ParameterizedImportTaskfile"
    version: str = "v0.0.1"
    severity: Severity = Severity.MEDIUM
    tags: tuple = Tag.DEPENDENCY

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        # import_tasks: xxx.yml
        #   or
        # import_tasks:
        #   file: yyy.yml

        taskfile_ref_arg = task.args.get("file")
        if not taskfile_ref_arg:
            taskfile_ref_arg = task.args

        verdict = task.action_type == ActionType.TASKFILE_TYPE and taskfile_ref_arg and taskfile_ref_arg.is_mutable
        taskfile_ref = taskfile_ref_arg.raw if taskfile_ref_arg else None
        detail = {
            "taskfile": taskfile_ref,
        }

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
