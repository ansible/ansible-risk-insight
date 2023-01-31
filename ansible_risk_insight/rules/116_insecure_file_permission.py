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

from ansible_risk_insight.models import DefaultRiskType as RiskType
from ansible_risk_insight.models import AnsibleRunContext, RunTargetType, AnnotationCondition
from ansible_risk_insight.rules.base import Rule, Severity, Tag, RuleResult


class FilePermissionRuleResult(RuleResult):
    pass


class FilePermissionRule(Rule):
    rule_id: str = "R116"
    description: str = "File permission is not secure."
    enabled: bool = False
    name: str = "FilePermissionRule"
    version: str = "v0.0.1"
    severity: Severity = Severity.LOW
    tags: list = [Tag.SYSTEM]
    result_type: type = FilePermissionRuleResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        # define a condition for this rule here
        ac = AnnotationCondition().risk_type(RiskType.FILE_CHANGE).attr("is_insecure_permissions", True)
        result = task.has_annotation(ac)

        rule_result = self.create_result(result=result, task=task)
        return rule_result