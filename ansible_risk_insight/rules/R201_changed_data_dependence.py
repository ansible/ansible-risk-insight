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
    RuleResult,
)


@dataclass
class ChangedDataDependenceRule(Rule):
    rule_id: str = "R201"
    description: str = "A variable is re-defined"
    enabled: bool = True
    name: str = "ChangedDataDependence"
    version: str = "v0.0.1"
    severity: Severity = Severity.VERY_LOW
    tags: tuple = Tag.VARIABLE

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = False
        detail = {"variables": []}
        if task.spec.defined_vars:
            for v in task.spec.defined_vars:
                all_definitions = task.variable_set.get(v, [])
                if len(all_definitions) > 1:
                    detail["variables"].append(
                        {
                            "name": v,
                            "defined_by": [d.setter for d in all_definitions],
                        }
                    )
                    verdict = True

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
