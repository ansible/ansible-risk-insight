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
from ansible_risk_insight.models import TaskCall, RiskAnnotation
from ansible_risk_insight.utils import load_classes_in_dir
from ansible_risk_insight.annotators.annotator_base import Annotator, AnnotatorResult
from ansible_risk_insight.annotators.module_annotator_base import ModuleAnnotator, ModuleAnnotatorResult


class RiskAnnotator(Annotator):
    type: str = RiskAnnotation.type
    name: str = ""
    enabled: bool = False

    module_annotator_cache: dict = {}

    def match(self, task: TaskCall) -> bool:
        raise ValueError("this is a base class method")

    def run(self, task: TaskCall):
        raise ValueError("this is a base class method")

    def load_module_annotators(self, dir_path: str):
        if dir_path in self.module_annotator_cache:
            return self.module_annotator_cache[dir_path]

        annotator_classes, _ = load_classes_in_dir(dir_path, ModuleAnnotator, __file__)
        module_annotators = []
        for a_c in annotator_classes:
            annotator = a_c(context=self.context)
            module_annotators.append(annotator)
        if module_annotators:
            self.module_annotator_cache[dir_path] = module_annotators
        return module_annotators

    def run_module_annotators(self, dir_path: str, task: TaskCall) -> ModuleAnnotatorResult:
        if not dir_path:
            return []

        resolved_name = task.spec.resolved_name
        module_annotators = self.load_module_annotators(dir_path)

        # TODO: need to consider annotator precedence

        annotations = []

        for annotator in module_annotators:
            if not isinstance(annotator, ModuleAnnotator):
                continue
            if not annotator.fqcn:
                continue
            if resolved_name != annotator.fqcn:
                continue

            result = annotator.run(task)
            if not result:
                continue

            if result.annotations:
                annotations.extend(result.annotations)
        if annotations:
            return ModuleAnnotatorResult(annotations=annotations)
        return None


@dataclass
class RiskAnnotatorResult(AnnotatorResult):
    pass
