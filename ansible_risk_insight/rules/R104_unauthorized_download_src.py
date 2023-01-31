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
import re


allow_url_list = [
    "https://*"
]

deny_url_list = [
    "http://*"
]


@dataclass
class InvalidDownloadSourceRuleResult(RuleResult):
    pass


@dataclass
class InvalidDownloadSourceRule(Rule):
    rule_id: str = "R104"
    description: str = "A network transfer from unauthorized source is found."
    enabled: bool = True
    name: str = "InvalidDownloadSource"
    version: str = "v0.0.1"
    severity: Severity = Severity.HIGH
    tags: tuple = (Tag.NETWORK)
    result_type: type = InvalidDownloadSourceRuleResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        ac = AnnotationCondition().risk_type(RiskType.INBOUND)

        result = False
        detail = {}

        anno = task.get_annotation(ac)
        if anno:
            if not self.is_allowed_url(anno.src.value, allow_url_list, deny_url_list):
                result = True
                detail["invalid_src"] = anno.src.value

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result

    def is_allowed_url(self, src, allow_list, deny_list):
        matched = True
        if len(allow_list) > 0:
            matched = False
            for a in allow_list:
                res = re.match(a, src)
                if res:
                    matched = True
        elif len(deny_list) > 0:
            for d in deny_list:
                res = re.match(d, src)
                if res:
                    matched = False
        return matched
