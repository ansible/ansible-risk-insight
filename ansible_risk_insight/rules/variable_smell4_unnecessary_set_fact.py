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

from ansible_risk_insight.models import AnsibleRunContext, RunTargetType, ExecutableType as ActionType
from ansible_risk_insight.rules.base import Rule, Severity, Tag


@dataclass
class UnnecessarySetFactRule(Rule):
    rule_id: str = "R205"
    description: str = "set_fact is used without random filter"
    enabled: bool = True
    name: str = "UnnecessarySetFact"
    version: str = "v0.0.1"
    severity: Severity = Severity.LOW
    tags: tuple = Tag.VARIABLE

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        args = task.args.raw
        is_impure = False
        detail = {}
        if isinstance(args, str):
            is_impure = "random" in args
            detail["impure_args"] = args
        elif isinstance(args, dict):
            for v in args.values():
                if isinstance(v, str) and "random" in v:
                    is_impure = True
                    current = detail.get("impure_args", [])
                    detail["impure_args"] = current.append(v)

        result = (
            task.action_type == ActionType.MODULE_TYPE and task.resolved_action and task.resolved_action == "ansible.builtin.set_fact" and is_impure
        )

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
