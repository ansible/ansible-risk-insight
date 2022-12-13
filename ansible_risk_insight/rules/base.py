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

_severity_level_mapping = {
    "very_high": 5,
    "high": 4,
    "medium": 3,
    "low": 2,
    "very_low": 1,
}


class SeverityValue:
    _name: str
    _level: int

    def __init__(self, level_str):
        if level_str not in _severity_level_mapping:
            raise ValueError(f"{level_str} is not valid severity level string")
        self._name = level_str
        self._level = _severity_level_mapping[level_str]

    def __eq__(self, other):
        if not isinstance(other, SeverityValue):
            return NotImplemented
        return self._level == other._level

    def __lt__(self, other):
        if not isinstance(other, SeverityValue):
            return NotImplemented
        return self._level < other._level

    def __ne__(self, other):
        return not self.__eq__(other)

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __str__(self):
        return self._name


# following ansible-lint severity levels
class Severity:
    VERY_HIGH = SeverityValue("very_high")
    HIGH = SeverityValue("high")
    MEDIUM = SeverityValue("medium")
    LOW = SeverityValue("low")
    VERY_LOW = SeverityValue("very_low")


class Rule(object):
    name: str = ""
    enabled: bool = False
    severity: SeverityValue = None
    tags: list = []
    separate_report: bool = False
    all_ok_message: str = ""

    def is_target(self, type: str, name: str) -> bool:
        raise ValueError("this is a base class method")

    def check(self, taskcalls: List[TaskCall], **kwargs):
        raise ValueError("this is a base class method")
