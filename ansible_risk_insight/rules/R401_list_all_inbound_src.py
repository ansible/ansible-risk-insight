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
class ListAllInboundSrcRuleResult(RuleResult):
    pass


@dataclass
class ListAllInboundSrcRule(Rule):
    rule_id: str = "R401"
    description: str = "List all inbound sources"
    enabled: bool = True
    name: str = "ListAllInboundSrcRule"
    version: str = "v0.0.1"
    severity: Severity = Severity.VERY_LOW
    tags: tuple = Tag.DEBUG
    result_type: type = ListAllInboundSrcRuleResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        ac = AnnotationCondition().risk_type(RiskType.INBOUND)
        result = False
        detail = {}
        src_list = []
        if ctx.is_end(task):
            tasks = ctx.search(ac)
            for t in tasks:
                anno = t.get_annotation(ac)
                if anno:
                    src_list.append(anno.src.value)
            if len(src_list) > 0:
                result = True
                detail["inbound_src"] = src_list

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
