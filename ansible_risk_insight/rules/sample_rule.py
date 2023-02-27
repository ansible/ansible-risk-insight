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
    RuleResult,
)


@dataclass
class SampleRule(Rule):
    rule_id: str = "Sample101"
    description: str = "echo task block"
    enabled: bool = False
    name: str = "EchoTaskContent"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = ("sample")

    def match(self, ctx: AnsibleRunContext) -> bool:
        # specify targets to be checked
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = True
        detail = {}
        task_block = task.content.yaml()
        detail["task_block"] = task_block

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
