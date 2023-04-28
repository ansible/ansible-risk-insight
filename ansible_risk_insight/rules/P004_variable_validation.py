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
    RuleTag as Tag,
    VariableType,
    ArgumentsType,
)


def is_loop_var(value, task):
    # `item` or alternative loop variable (if any) should not be replaced to avoid breaking loop
    skip_variables = []
    if task.spec.loop and isinstance(task.spec.loop, dict):
        skip_variables.extend(list(task.spec.loop.keys()))

    _v = value.replace(" ", "")

    for var in skip_variables:
        for _prefix in ["}}", "|", "."]:
            pattern = "{{" + var + _prefix
            if pattern in _v:
                return True
    return False


@dataclass
class VariableValidationRule(Rule):
    rule_id: str = "P004"
    description: str = "Validate variables and set annotations"
    enabled: bool = True
    name: str = "VariableValidation"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.QUALITY
    precedence: int = 0

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        undefined_variables = []
        unknown_name_vars = []
        unnecessary_loop = []
        task_arg_keys = []
        if task.args.type == ArgumentsType.DICT:
            task_arg_keys = list(task.args.raw.keys())
        for v_name in task.variable_use:
            v = task.variable_use[v_name]
            if v and v[-1].type == VariableType.Unknown:
                if v_name not in undefined_variables:
                    undefined_variables.append(v_name)
                if v_name not in unknown_name_vars and v_name not in task_arg_keys:
                    unknown_name_vars.append(v_name)
                if v_name not in unnecessary_loop:
                    v_str = "{{ " + v_name + " }}"
                    if not is_loop_var(v_str, task):
                        unnecessary_loop.append({"name": v_name, "suggested": v_name.replace("item.", "")})

        task.set_annotation("variable.undefined_vars", undefined_variables, rule_id=self.rule_id)
        task.set_annotation("variable.unknown_name_vars", unknown_name_vars, rule_id=self.rule_id)
        task.set_annotation("variable.unnecessary_loop_vars", unnecessary_loop, rule_id=self.rule_id)

        return None
