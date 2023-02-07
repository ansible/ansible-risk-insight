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
class NonFQCNUseRule(Rule):
    rule_id: str = "R301"
    description: str = "A task with a short module name is found"
    enabled: bool = True
    name: str = "NonFQCNUse"
    version: str = "v0.0.1"
    severity: Severity = Severity.VERY_LOW
    tags: tuple = Tag.DEPENDENCY

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = (
            task.action_type == ActionType.MODULE_TYPE
            and task.spec.action
            and task.resolved_action
            and task.spec.action != task.resolved_action
            and not task.resolved_action.startswith("ansible.builtin.")
        )
        detail = {
            "module": task.spec.action,
            "fqcn": task.resolved_name,
        }

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
