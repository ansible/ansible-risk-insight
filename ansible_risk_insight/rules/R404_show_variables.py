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

from ansible_risk_insight.models import AnsibleRunContext, RunTargetType, VariableDict
from ansible_risk_insight.rules.base import Rule, Severity, Tag, RuleResult


@dataclass
class ShowVariablesRuleResult(RuleResult):
    def print(self):
        variables = self.detail["variables"]
        var_table = "None"
        if variables:
            var_table = "\n" + VariableDict.print_table(variables)
        output = f"ruleID={self._rule.rule_id}, \
            severity={self._rule.severity}, \
            description={self._rule.description}, \
            result={self.result}, \
            file={self.file}, \
            lines={self.lines}, \
            variables={var_table}\n"
        return output


@dataclass
class ShowVariablesRule(Rule):
    rule_id: str = "R404"
    description: str = "Show all variables"
    enabled: bool = True
    name: str = "ShowVariables"
    version: str = "v0.0.1"
    severity: Severity = Severity.LOW
    tags: tuple = (Tag.VARIABLE)
    result_type: type = ShowVariablesRuleResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        result = True
        detail = {"variables": task.variable_set}

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
