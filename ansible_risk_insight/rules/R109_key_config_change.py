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
    DefaultRiskType as RiskType,
    AnnotationCondition,
    Rule,
    Severity,
    RuleTag as Tag,
    RuleResult,
)


@dataclass
class KeyConfigChangeResult(RuleResult):
    pass


@dataclass
class KeyConfigChangeRule(Rule):
    rule_id: str = "R109"
    description: str = "Key configuration is changed"
    enabled: bool = True
    name: str = "ConfigChange"
    version: str = "v0.0.1"
    severity: Severity = Severity.LOW
    tags: tuple = Tag.SYSTEM
    result_type: type = KeyConfigChangeResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        ac = AnnotationCondition().risk_type(RiskType.CONFIG_CHANGE).attr("is_mutable_key", True)
        result = task.has_annotation(ac)

        detail = {}
        if result:
            anno = task.get_annotation(ac)
            if anno:
                detail["key"] = anno.key

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
