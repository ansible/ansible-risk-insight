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

from typing import List
from ..models import RiskAnnotation, TaskCall
from ..annotators.risk_annotator_base import AnnotatorCategory, RISK_ANNOTATION_TYPE
from .base import Rule, Severity, Tag


class OutboundTransferRule(Rule):
    enabled: bool = True
    name: str = "OutboundTransfer"
    version: str = "v0.0.1"
    severity: Severity = Severity.MEDIUM
    tags: list = [Tag.NETWORK]

    def is_target(self, type: str, name: str) -> bool:
        return True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        matched_taskcalls = []
        message = ""
        for taskcall in taskcalls:
            outbound_annos = taskcall.get_annotation_by_type_and_attr(RISK_ANNOTATION_TYPE, "category", AnnotatorCategory.OUTBOUND)
            for outbound_data in outbound_annos:
                if not isinstance(outbound_data, RiskAnnotation):
                    continue
                raw_src = outbound_data.data.get("src", "")
                resolved_dst = [resolved.get("dest", "") for resolved in outbound_data.resolved_data if resolved.get("dest", "") != ""]
                if len(resolved_dst) == 0:
                    resolved_dst = ""
                if len(resolved_dst) == 1:
                    resolved_dst = resolved_dst[0]
                is_mutable_dst = outbound_data.data.get("undetermined_dest", False)
                mutable_dst_vars = outbound_data.data.get("mutable_dest_vars", [])
                mutable_dst_vars = ["{{ " + mv + " }}" for mv in mutable_dst_vars]
                if len(mutable_dst_vars) == 0:
                    mutable_dst_vars = ""
                if len(mutable_dst_vars) == 1:
                    mutable_dst_vars = mutable_dst_vars[0]
                if is_mutable_dst:
                    matched_taskcalls.append(taskcall)
                    message += "- From: {}\n".format(raw_src)
                    message += "  To: {}\n".format(mutable_dst_vars)
                    # message += "      (default value: {})\n".format(
                    #     resolved_dst
                    # )
        matched = len(matched_taskcalls) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_taskcalls, message
