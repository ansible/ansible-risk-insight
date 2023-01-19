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
from ansible_risk_insight.models import TaskCall
from ansible_risk_insight.annotators.annotator_base import Annotator, AnnotatorResult


class ModuleAnnotator(Annotator):
    type: str = "module_annotation"
    fqcn: str = "<module FQCN to be annotated by this>"

    def run(self, task: TaskCall) -> AnnotatorResult:
        raise ValueError("this is a base class method")


@dataclass
class ModuleAnnotatorResult(AnnotatorResult):
    pass
