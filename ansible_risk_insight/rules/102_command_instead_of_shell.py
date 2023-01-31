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

from ansible_risk_insight.models import AnsibleRunContext, ExecutableType as ActionType, RunTargetType
from ansible_risk_insight.rules.base import Rule, Severity, Tag, RuleResult


class UseShellResult(RuleResult):
    pass


class UseShellRule(Rule):
    rule_id: str = "R102"
    description: str = "Use 'command' module instead of 'shell' "
    enabled: bool = True
    name: str = "UseShellRule"
    version: str = "v0.0.1"
    severity: Severity = Severity.VERY_LOW
    tags: list = [Tag.DEBUG]
    result_type: type = UseShellResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        # define a condition for this rule here
        result = task.action_type == ActionType.MODULE_TYPE and \
            task.spec.action and \
            task.resolved_action and \
            task.resolved_action == "ansible.builtin.shell"

        rule_result = self.create_result(result=result, task=task)
        return rule_result
