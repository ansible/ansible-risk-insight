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
from ..models import Annotation, TaskCall
from .annotator_base import Annotator


RISK_ANNOTATION_TYPE = "risk_annotation"


class RiskType:
    NONE = ""
    CMD_EXEC = "cmd_exec"
    INBOUND = "inbound_transfer"
    OUTBOUND = "outbound_transfer"
    FILE_CHANGE = "file_change"
    SYSTEM_CHANGE = "system_change"
    NETWORK_CHANGE = "network_change"
    CONFIG_CHANGE = "config_change"
    PACKAGE_INSTALL = "package_install"
    PRIVILEGE_ESCALATION = "privilege_escalation"


class RiskAnnotator(Annotator):
    type: str = RISK_ANNOTATION_TYPE
    name: str = ""
    enabled: bool = False

    def match(self, taskcall: TaskCall) -> bool:
        raise ValueError("this is a base class method")

    def run(self, taskcall: TaskCall) -> List[Annotation]:
        raise ValueError("this is a base class method")
