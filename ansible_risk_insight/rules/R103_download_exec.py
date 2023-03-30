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
    DefaultRiskType as RiskType,
    AnnotationCondition,
    Rule,
    Severity,
    RuleTag as Tag,
    RuleResult,
)


@dataclass
class DownloadExecRule(Rule):
    rule_id: str = "R103"
    description: str = "A downloaded file from parameterized source is executed"
    enabled: bool = True
    name: str = "Download & Exec"
    version: str = "v0.0.1"
    severity: Severity = Severity.HIGH
    tags: tuple = (Tag.NETWORK, Tag.COMMAND)
    precedence: int = 11

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = False
        detail = {}

        ac = AnnotationCondition().risk_type(RiskType.CMD_EXEC)
        if task.has_annotation_by_condition(ac):
            cmd_an = task.get_annotation_by_condition(ac)
            if cmd_an:
                detail["command"] = cmd_an.command.raw

            ac2 = AnnotationCondition().risk_type(RiskType.INBOUND).attr("is_mutable_src", True)
            inbound_tasks = ctx.before(task).search(ac2)
            for inbound_task in inbound_tasks:
                inbound_an = inbound_task.get_annotation_by_condition(ac2)
                if not inbound_an:
                    continue
                detail["src"] = inbound_an.src.value

                # check if any of the exec_files are inside the download location
                # if so, the downloaded file is executed, so we report it
                download_location = inbound_an.dest
                executed_files = cmd_an.exec_files
                matched_files = [f for f in executed_files if f.is_inside(download_location)]
                if matched_files:
                    detail["executed_file"] = [f.value for f in matched_files]
                    verdict = True

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
