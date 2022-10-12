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
from ..models import TaskCall
from .base import Rule


class SampleCustomRule(Rule):
    name: str = "SampleCustomRule"
    enabled: bool = False

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        # this sample rule checks if each task has a name
        matched_tasks = []
        message = ""
        # define a condition for this rule here
        for taskcall in taskcalls:
            if taskcall.spec.name == "":
                matched_tasks.append(taskcall)
        message = "{} task(s) don't have the names".format(len(matched_tasks))
        # end of the condition
        matched = len(matched_tasks) > 0
        return matched, matched_tasks, message
