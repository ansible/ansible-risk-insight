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
from typing import List
from ansible_risk_insight.models import TaskCall, AnsibleRunContext, Annotation


class Annotator(object):
    type: str = ""
    context: AnsibleRunContext = None

    def __init__(self, context: AnsibleRunContext = None):
        if context:
            self.context = context

    def run(self, task: TaskCall):
        raise ValueError("this is a base class method")


@dataclass
class AnnotatorResult(object):
    annotations: List[Annotation] = None
    data: any = None

    def print(self):
        raise ValueError("this is a base class method")

    def to_json(self):
        raise ValueError("this is a base class method")

    def error(self):
        raise ValueError("this is a base class method")
