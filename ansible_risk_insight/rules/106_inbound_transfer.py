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
class InboundRuleResult(RuleResult):
    pass


@dataclass
class InboundTransferRule(Rule):
    rule_id: str = "R106"
    description: str = "A inbound network transfer from a parameterized source is found"
    enabled: bool = True
    name: str = "InboundTransfer"
    version: str = "v0.0.1"
    severity: Severity = Severity.MEDIUM
    tags: tuple = Tag.NETWORK
    result_type: type = InboundRuleResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        ac = AnnotationCondition().risk_type(RiskType.INBOUND).attr("is_mutable_src", True)
        result = task.has_annotation(ac)

        detail = {}
        if result:
            anno = task.get_annotation(ac)
            if anno:
                detail["from"] = anno.src.value
                detail["to"] = anno.dest.value

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
