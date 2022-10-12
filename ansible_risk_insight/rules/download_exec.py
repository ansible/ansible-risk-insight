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
from ..annotators.base import RiskType, RISK_ANNOTATION_TYPE
from .base import Rule


non_execution_programs: list = ["tar", "gunzip", "unzip", "mv", "cp"]


class DownloadExecRule(Rule):
    name: str = "Download & Exec"
    enabled: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        # list downloaded files from "inbound_transfer" tasks
        download_files_and_tasks = []
        for taskcall in taskcalls:
            inbound_annos = taskcall.get_annotation_by_type_and_attr(RISK_ANNOTATION_TYPE, "category", RiskType.INBOUND)
            for inbound_data in inbound_annos:
                if not isinstance(inbound_data, RiskAnnotation):
                    continue
                dst = inbound_data.data.get("dest", "")
                is_mutable_src = inbound_data.data.get("undetermined_src", False)
                if not is_mutable_src:
                    continue
                mutable_src_vars = inbound_data.data.get("mutable_src_vars", [])
                mutable_src_vars = ["{{ " + mv + " }}" for mv in mutable_src_vars]
                if len(mutable_src_vars) == 0:
                    mutable_src_vars = ""
                if len(mutable_src_vars) == 1:
                    mutable_src_vars = mutable_src_vars[0]
                if isinstance(dst, str) and dst != "":
                    download_files_and_tasks.append((dst, taskcall, mutable_src_vars))
                elif isinstance(dst, list) and len(dst) > 0:
                    for _d in dst:
                        download_files_and_tasks.append((_d, taskcall, mutable_src_vars))
        # check if the downloaded files are executed in "cmd_exec" tasks
        matched_taskcalls = []
        message = ""
        found = []
        exec_count = 0
        for taskcall in taskcalls:
            exec_annos = taskcall.get_annotation_by_type_and_attr(RISK_ANNOTATION_TYPE, "category", RiskType.CMD_EXEC)
            if len(exec_annos) > 0:
                exec_count += 1
            for exec_data in exec_annos:
                if not isinstance(exec_data, RiskAnnotation):
                    continue
                cmd_str = exec_data.data.get("cmd", "")
                if isinstance(cmd_str, list):
                    cmd_str = " ".join(cmd_str)
                for i, (
                    downloaded_file,
                    download_taskcall,
                    download_mutable_src_vars,
                ) in enumerate(download_files_and_tasks):
                    if i in found:
                        continue
                    if _is_executed(cmd_str, downloaded_file):
                        matched_taskcalls.append((download_taskcall, taskcall))
                        found.append(i)
                        message += "- Download block: {}, line: {}\n".format(
                            download_taskcall.spec.defined_in,
                            _make_line_num_expr(download_taskcall.spec.line_num_in_file),
                        )
                        message += "  Exec block: {}, line: {}\n".format(
                            taskcall.spec.defined_in,
                            _make_line_num_expr(taskcall.spec.line_num_in_file),
                        )
                        message += "  Mutable Variables: {}\n".format(download_mutable_src_vars)
        matched = len(matched_taskcalls) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_taskcalls, message


def _make_line_num_expr(line_num_parts: list):
    line_num_expr = "?"
    if len(line_num_parts) == 2:
        line_num_expr = "{} - {}".format(line_num_parts[0], line_num_parts[1])
    return line_num_expr


def _is_executed(cmd_str, target):
    lines = cmd_str.splitlines()
    found = False
    for line in lines:
        if target not in line:
            continue
        if line.startswith(target):
            found = True
        if _is_primary_command_target(line, target):
            found = True
        if found:
            break
    return found


def _is_primary_command_target(line, target):
    parts = []
    is_in_variable = False
    concat_p = ""
    for p in line.split(" "):
        if "{{" in p and "}}" not in p:
            is_in_variable = True
        if "}}" in p:
            is_in_variable = False
        concat_p += " " + p if concat_p != "" else p
        if not is_in_variable:
            parts.append(concat_p)
            concat_p = ""
    current_index = 0
    found_index = -1
    for p in parts:
        if current_index == 0:
            program = p if "/" not in p else p.split("/")[-1]
            # filter out some specific non-exec patterns
            if program in non_execution_programs:
                break
        if p.startswith(target):
            found_index = current_index
            break
        if p.startswith("-"):
            continue
        current_index += 1
    # "<target.sh> option1 option2" => found_index == 0
    # python -u <target.py> ==> found_index == 1
    is_primay_target = found_index >= 0 and found_index <= 1
    return is_primay_target
