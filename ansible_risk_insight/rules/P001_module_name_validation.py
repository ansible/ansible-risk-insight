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
    ExecutableType,
)


@dataclass
class ModuleNameValidationRule(Rule):
    rule_id: str = "P001"
    description: str = "Validate a module name and set annotations"
    enabled: bool = True
    name: str = "ModuleNameValidation"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.QUALITY
    precedence: int = 0

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        if task.spec.executable_type == ExecutableType.MODULE_TYPE:

            suggested_fqcns = [cand[0] for cand in task.spec.possible_candidates]
            suggested_dependency = [cand[1] for cand in task.spec.possible_candidates]

            wrong_module_name = ""
            not_exist = False
            if not task.spec.resolved_name:
                for suggestion in suggested_fqcns:
                    if not suggestion.endswith(f".{task.spec.module}"):
                        wrong_module_name = task.spec.module
                        break
                if not task.spec.possible_candidates:
                    not_exist = True
                    wrong_module_name = task.spec.module
            correct_fqcn = ""
            if task.spec.resolved_name:
                correct_fqcn = task.spec.resolved_name
            elif suggested_fqcns:
                correct_fqcn = suggested_fqcns[0]

            need_correction = False
            if correct_fqcn != task.spec.module or not_exist:
                need_correction = True

            task.set_annotation("module.suggested_fqcn", suggested_fqcns, rule_id=self.rule_id)
            task.set_annotation("module.suggested_dependency", suggested_dependency, rule_id=self.rule_id)
            task.set_annotation("module.resolved_fqcn", task.spec.resolved_name, rule_id=self.rule_id)
            task.set_annotation("module.wrong_module_name", wrong_module_name, rule_id=self.rule_id)
            task.set_annotation("module.not_exist", not_exist, rule_id=self.rule_id)
            task.set_annotation("module.correct_fqcn", correct_fqcn, rule_id=self.rule_id)
            task.set_annotation("module.need_correction", need_correction, rule_id=self.rule_id)

        return None
