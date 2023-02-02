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
    Rule,
    Severity,
    RuleTag as Tag,
)


@dataclass
class ListAllUsedVariablesRule(Rule):
    rule_id: str = "R402"
    description: str = "Listing all used variables"
    enabled: bool = True
    name: str = "ListAllUsedVariables"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.VARIABLE

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        result = False
        detail = {}
        if ctx.is_end(task):

            result = True
            detail["metadata"] = ctx.info
            detail["variables"] = list(task.variable_use.keys())

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
