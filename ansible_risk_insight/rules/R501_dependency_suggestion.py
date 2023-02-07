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
class DependencySuggestionRule(Rule):
    rule_id: str = "R501"
    description: str = "Suggest dependencies for unresolved modules/roles"
    enabled: bool = True
    name: str = "DependencySuggestion"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.DEPENDENCY

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = False
        detail = {}
        if task.spec.possible_candidates:
            verdict = True
            detail["type"] = task.spec.executable_type.lower()
            detail["fqcn"] = task.spec.possible_candidates[0][0]
            req_info = task.spec.possible_candidates[0][1]
            detail["suggestion"] = {}
            detail["suggestion"]["type"] = req_info.get("type", "")
            detail["suggestion"]["name"] = req_info.get("name", "")
            detail["suggestion"]["version"] = req_info.get("version", "")

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
