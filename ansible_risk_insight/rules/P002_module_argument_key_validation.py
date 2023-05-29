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
    ActionGroupMetadata,
)


def is_set_fact(module_fqcn):
    return module_fqcn == "ansible.builtin.set_fact"


@dataclass
class ModuleArgumentKeyValidationRule(Rule):
    rule_id: str = "P002"
    description: str = "Validate module argument keys and set annotations"
    enabled: bool = True
    name: str = "ModuleArgumentKeyValidation"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    tags: tuple = Tag.QUALITY
    precedence: int = 0

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        if task.spec.executable_type == ExecutableType.MODULE_TYPE and task.module and task.module.arguments:

            mo = task.spec.module_options
            module_fqcn = task.get_annotation(key="module.correct_fqcn")
            module_short = ""
            if module_fqcn:
                parts = module_fqcn.split(".")
                if len(parts) <= 2:
                    module_short = module_fqcn.split(".")[-1]
                elif len(parts) > 2:
                    module_short = ".".join(module_fqcn.split(".")[2:])
            default_args = {}
            if module_short and module_short in task.module_defaults:
                default_args = task.module_defaults[module_short]
            elif module_fqcn and module_fqcn in task.module_defaults:
                default_args = task.module_defaults[module_fqcn]
            elif ctx.ram_client:
                for group_name in task.module_defaults:
                    tmp_args = task.module_defaults[group_name]
                    found = False
                    if not group_name.startswith("group/"):
                        continue
                    groups = ctx.ram_client.search_action_group(group_name)
                    if not groups:
                        continue
                    for group_dict in groups:
                        if not group_dict:
                            continue
                        if not isinstance(group_dict, dict):
                            continue
                        group = ActionGroupMetadata.from_dict(group_dict)
                        if module_short and module_short in group.group_modules:
                            found = True
                            default_args = tmp_args
                            break
                        elif module_fqcn and module_fqcn in group.group_modules:
                            found = True
                            default_args = tmp_args
                            break
                    if found:
                        break

            used_keys = []
            if isinstance(mo, dict):
                used_keys = list(mo.keys())

            available_keys = []
            required_keys = []
            alias_reverse_map = {}
            available_args = None
            wrong_keys = []
            missing_required_keys = []
            if not is_set_fact(module_fqcn):
                if task.module:
                    for arg in task.module.arguments:
                        available_keys.extend(arg.available_keys())
                        if arg.required:
                            aliases = arg.aliases if arg.aliases else []
                            req_k = {"key": arg.name, "aliases": aliases}
                            required_keys.append(req_k)
                        if arg.aliases:
                            for al in arg.aliases:
                                alias_reverse_map[al] = arg.name
                    available_args = task.module.arguments

                wrong_keys = [key for key in used_keys if key not in available_keys]

                for k in required_keys:
                    name = k.get("key", "")
                    aliases = k.get("aliases", [])
                    if name in used_keys:
                        continue
                    if name in default_args:
                        continue
                    if aliases:
                        found = False
                        for a_k in aliases:
                            if a_k in used_keys:
                                found = True
                                break
                            if a_k in default_args:
                                found = True
                                break
                        if found:
                            continue
                    # here, the required key was not found
                    missing_required_keys.append(name)

            used_alias_and_real_keys = []
            for k in used_keys:
                if k not in alias_reverse_map:
                    continue
                real_name = alias_reverse_map[k]
                used_alias_and_real_keys.append(
                    {
                        "used_alias": k,
                        "real_key": real_name,
                    }
                )

            task.set_annotation("module.wrong_arg_keys", wrong_keys, rule_id=self.rule_id)
            task.set_annotation("module.available_arg_keys", available_keys, rule_id=self.rule_id)
            task.set_annotation("module.required_arg_keys", required_keys, rule_id=self.rule_id)
            task.set_annotation("module.missing_required_arg_keys", missing_required_keys, rule_id=self.rule_id)
            task.set_annotation("module.available_args", available_args, rule_id=self.rule_id)
            task.set_annotation("module.default_args", default_args, rule_id=self.rule_id)
            task.set_annotation("module.used_alias_and_real_keys", used_alias_and_real_keys, rule_id=self.rule_id)

        # TODO: find duplicate keys

        return None
