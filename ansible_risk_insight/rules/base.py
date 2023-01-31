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

import json
from dataclasses import dataclass
from ansible_risk_insight.models import AnsibleRunContext


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
    CODING = "coding"
    VARIABLE = "variable"
    DEBUG = "debug"


@dataclass
class RuleResult(object):
    result: bool = False
    file: str = None
    lines: str = None
    detail: dict = None
    error_msg: str = None

    verbose: bool = False

    _rule: any = None

    def __post_init__(self):
        if self.result:
            self.result = True
        else:
            self.result = False

    def print(self):
        output = f"ruleID={self._rule.rule_id}, severity={self._rule.severity}, description={self._rule.description}, result={self.result}"
        if self.verbose:
            output += f", name={self._rule.name}, version={self._rule.version}, tags={self._rule.version}"

        if self.file:
            output += f", file={self.file}"
        if self.lines:
            output += f", lines={self.lines}"
        if self.detail:
            output += f", detail={self.detail}"
        return output

    def to_json(self, detail=None):
        return json.dumps(detail)

    def error(self):
        if self.error_msg:
            return self.error_msg
        return None


@dataclass
class Rule(object):
    rule_id: str = ""
    description: str = ""

    name: str = ""
    enabled: bool = False
    version: str = ""
    severity: str = ""
    tags: tuple = ()
    separate_report: bool = False
    all_ok_message: str = ""

    result_type: type = RuleResult

    def __post_init__(self, rule_id: str = "", description: str = ""):
        if rule_id:
            self.rule_id = rule_id
        if description:
            self.description = description

        if not self.rule_id:
            raise ValueError("A rule must have a unique rule_id")

        if not self.description:
            raise ValueError("A rule must have a description")

    def match(self, ctx: AnsibleRunContext) -> bool:
        raise ValueError("this is a base class method")

    def check(self, ctx: AnsibleRunContext):
        raise ValueError("this is a base class method")

    def create_result(self, result=False, detail=None, task=None, role=None, playbook=None):
        file = None
        lines = None
        if task:
            file = task.spec.defined_in
            lines = "?"
            if len(task.spec.line_number) == 2:
                l_num = task.spec.line_number
                lines = f"L{l_num[0]}-{l_num[1]}"
        elif role:
            file = role.spec.defined_in
        elif playbook:
            file = playbook.spec.defined_in

        return self.result_type(result=result, file=file, lines=lines, detail=detail, _rule=self)
