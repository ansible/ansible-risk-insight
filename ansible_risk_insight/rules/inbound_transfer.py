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
from ..annotators.risk_annotator_base import RiskType, RISK_ANNOTATION_TYPE
from .base import Rule


class InboundTransferRule(Rule):
    name: str = "InboundTransfer"
    enabled: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        matched_taskcalls = []
        message = ""
        for taskcall in taskcalls:
            inbound_annos = taskcall.get_annotation_by_type_and_attr(RISK_ANNOTATION_TYPE, "category", RiskType.INBOUND)
            for inbound_data in inbound_annos:
                if not isinstance(inbound_data, RiskAnnotation):
                    continue
                raw_dst = inbound_data.data.get("dest", "")
                resolved_src = [resolved.get("src", "") for resolved in inbound_data.resolved_data if resolved.get("src", "") != ""]
                if len(resolved_src) == 0:
                    resolved_src = ""
                if len(resolved_src) == 1:
                    resolved_src = resolved_src[0]
                is_mutable_src = inbound_data.data.get("undetermined_src", False)
                mutable_src_vars = inbound_data.data.get("mutable_src_vars", [])
                mutable_src_vars = ["{{ " + mv + " }}" for mv in mutable_src_vars]
                if len(mutable_src_vars) == 0:
                    mutable_src_vars = ""
                if len(mutable_src_vars) == 1:
                    mutable_src_vars = mutable_src_vars[0]
                if is_mutable_src:
                    matched_taskcalls.append(taskcall)
                    message += "- From: {}\n".format(mutable_src_vars)
                    # message += "      (default value: {})\n".format(
                    #     resolved_src
                    # )
                    message += "  To: {}\n".format(raw_dst)
        matched = len(matched_taskcalls) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_taskcalls, message
