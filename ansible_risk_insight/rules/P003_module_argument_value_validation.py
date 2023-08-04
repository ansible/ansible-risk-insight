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
    ArgumentsType,
    ExecutableType,
    VariableType,
)


def is_loop_var(value, task):
    # `item` and alternative loop variable (if any) should not be replaced to avoid breaking loop
    skip_variables = ["item"]
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
class ModuleArgumentValueValidationRule(Rule):
    rule_id: str = "P003"
    description: str = "Validate module argument values and set annotations"
    enabled: bool = True
    name: str = "ModuleArgumentValueValidation"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.QUALITY
    precedence: int = 0

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        if task.spec.executable_type == ExecutableType.MODULE_TYPE and task.module and task.module.arguments:

            wrong_values = []
            undefined_values = []
            unknown_type_values = []
            if task.args.type == ArgumentsType.DICT:
                for key in task.args.raw:
                    raw_value = task.args.raw[key]
                    resolved_value = None
                    if len(task.args.templated) >= 1:
                        resolved_value = task.args.templated[0][key]
                    spec = None
                    for arg_spec in task.module.arguments:
                        if key == arg_spec.name or (arg_spec.aliases and key in arg_spec.aliases):
                            spec = arg_spec
                            break
                    if not spec:
                        continue

                    d = {"key": key}
                    wrong_val = False
                    unknown_type_val = False
                    if spec.type:
                        actual_type = ""
                        # if the raw_value is not a variable
                        if not isinstance(raw_value, str) or "{{" not in raw_value:
                            actual_type = type(raw_value).__name__
                        else:
                            # otherwise, check the resolved value
                            # if the variable could not be resovled successfully
                            if isinstance(resolved_value, str) and "{{" in resolved_value:
                                pass
                            elif is_loop_var(raw_value, task):
                                # if the variable is loop var, use the element type as actual type
                                resolved_element = None
                                if resolved_value:
                                    resolved_element = resolved_value[0]
                                if resolved_element:
                                    actual_type = type(resolved_element).__name__
                            else:
                                # otherwise, use the resolved value type as actual type
                                actual_type = type(resolved_value).__name__

                        if actual_type:
                            type_wrong = False
                            if spec.type != "any" and actual_type != spec.type:
                                type_wrong = True
                            elements_type_wrong = False
                            no_elements = False
                            if spec.elements:
                                if spec.elements != "any" and actual_type != spec.elements:
                                    elements_type_wrong = True
                            else:
                                no_elements = True
                            if type_wrong and (elements_type_wrong or no_elements):
                                d["expected_type"] = spec.type
                                d["actual_type"] = actual_type
                                d["actual_value"] = raw_value
                                wrong_val = True
                        else:
                            d["expected_type"] = spec.type
                            d["unknown_type_value"] = resolved_value
                            unknown_type_val = True

                    if wrong_val:
                        wrong_values.append(d)

                    if unknown_type_val:
                        unknown_type_values.append(d)

                    sub_args = task.args.get(key)
                    if sub_args:
                        undefined_vars = [v.name for v in sub_args.vars if v and v.type == VariableType.Unknown]
                        if undefined_vars:
                            undefined_values.append({"key": key, "value": raw_value, "undefined_variables": undefined_vars})

            task.set_annotation("module.wrong_arg_values", wrong_values, rule_id=self.rule_id)
            task.set_annotation("module.undefined_values", undefined_values, rule_id=self.rule_id)
            task.set_annotation("module.unknown_type_values", unknown_type_values, rule_id=self.rule_id)

        # TODO: find duplicate keys

        return None
