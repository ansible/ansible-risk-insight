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
    VariableDict,
    RunTargetType,
    Rule,
    Severity,
    RuleTag as Tag,
    RuleResult,
)


@dataclass
class ShowVariablesRule(Rule):
    rule_id: str = "R404"
    description: str = "Show all variables"
    enabled: bool = False
    name: str = "ShowVariables"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.VARIABLE

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = True
        detail = {"variables": task.variable_set}

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())

    def print(self, result: RuleResult):
        variables = result.detail["variables"]
        var_table = "None"
        if variables:
            var_table = "\n" + VariableDict.print_table(variables)
        output = f"ruleID={self.rule_id}, \
            severity={self.severity}, \
            description={self.description}, \
            verdict={result.verdict}, \
            file={result.file}, \
            variables={var_table}\n"
        return output
