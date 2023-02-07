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
    RuleResult,
)


@dataclass
class ExternalRoleRuleResult(RuleResult):
    pass


@dataclass
class ExternalRoleRule(Rule):
    rule_id: str = "R117"
    description: str = "An external role is used"
    enabled: bool = True
    name: str = "ExternalRole"
    version: str = "v0.0.1"
    severity: Severity = Severity.VERY_LOW
    tags: tuple = Tag.DEPENDENCY
    result_type: type = ExternalRoleRuleResult

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Role

    def process(self, ctx: AnsibleRunContext):
        role = ctx.current

        verdict = (
            not ctx.is_begin(role) and role.spec.metadata and isinstance(role.spec.metadata, dict) and role.spec.metadata.get("galaxy_info", None)
        )

        return RuleResult(verdict=verdict, file=role.file_info(), rule=self.get_metadata())
