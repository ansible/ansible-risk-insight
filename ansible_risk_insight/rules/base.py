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


subject_placeholder = "<SUBJECT>"


# following ansible-lint severity levels
class Severity:
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


_severity_level_mapping = {
    Severity.VERY_HIGH: 5,
    Severity.HIGH: 4,
    Severity.MEDIUM: 3,
    Severity.LOW: 2,
    Severity.VERY_LOW: 1,
}


class Tag:
    NETWORK = "network"
    COMMAND = "command"
    DEPENDENCY = "dependency"
    SYSTEM = "system"
    PACKAGE = "package"
    DEBUG = "debug"


class Rule(object):
    name: str = ""
    enabled: bool = False
    version: str = ""
    severity: str = ""
    tags: list = []
    separate_report: bool = False
    all_ok_message: str = ""

    def is_target(self, type: str, name: str) -> bool:
        raise ValueError("this is a base class method")

    def check(self, taskcalls: List[TaskCall], **kwargs):
        raise ValueError("this is a base class method")
