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
from ansible_risk_insight.models import TaskCall, Annotation, RiskAnnotation, DefaultRiskType
from ansible_risk_insight.annotators.variable_resolver import VariableAnnotation
from ansible_risk_insight.annotators.risk_annotator_base import RiskAnnotator


class SampleCustomAnnotator(RiskAnnotator):
    name: str = "sample"
    enabled: bool = False

    # whether this task should be analyzed by this or not
    def match(self, taskcall: TaskCall) -> bool:
        # resolved_name = taskcall.resolved_name
        # return resolved_name.startswith("sample.custom.")
        return False

    # extract analyzed_data from task and embed it
    def run(self, task: TaskCall) -> List[Annotation]:
        resolved_name = task.spec.resolved_name
        options = task.spec.module_options
        var_annos = task.get_annotation_by_type(VariableAnnotation.type)
        var_anno = var_annos[0] if len(var_annos) > 0 else VariableAnnotation()
        resolved_options = var_anno.resolved_module_options

        annotations = []
        # example of package_install
        if resolved_name == "sample.custom.homebrew":
            res = RiskAnnotation(type=self.type, category=DefaultRiskType.PACKAGE_INSTALL)
            res.data = self.homebrew(options)
            for ro in resolved_options:
                res.resolved_data.append(self.homebrew(ro))
            annotations.append(res)
        return annotations

    def homebrew(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data
