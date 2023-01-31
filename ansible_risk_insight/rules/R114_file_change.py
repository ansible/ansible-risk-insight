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
from ansible_risk_insight.models import DefaultRiskType as RiskType
from ansible_risk_insight.models import AnsibleRunContext, RunTargetType, AnnotationCondition
from ansible_risk_insight.rules.base import Rule, Severity, Tag, RuleResult


@dataclass
class FileChangeResult(RuleResult):
    pass


@dataclass
class FileChangeRule(Rule):
    rule_id: str = "R114"
    description: str = "Parameterized file change is found"
    enabled: bool = True
    name: str = "ConfigChange"
    version: str = "v0.0.1"
    severity: Severity = Severity.LOW
    tags: tuple = (Tag.SYSTEM)
    result_type: type = FileChangeResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        ac = AnnotationCondition().risk_type(RiskType.FILE_CHANGE).attr("is_mutable_path", True)
        ac2 = AnnotationCondition().risk_type(RiskType.FILE_CHANGE).attr("is_mutable_src", True)
        result = False
        detail = {}
        if task.has_annotation(ac):
            result = True
            anno = task.get_annotation(ac)
            if anno:
                detail["path"] = anno.path.value

        if task.has_annotation(ac2):
            result = True
            anno = task.get_annotation(ac2)
            if anno:
                detail["src"] = anno.src.value

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
