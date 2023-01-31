# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2023 IBM Corp. All rights reserved.
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
from ansible_risk_insight.models import Annotation, RiskAnnotation, TaskCall, DefaultRiskType, PackageInstallDetail
from ansible_risk_insight.annotators.module_annotator_base import ModuleAnnotator, ModuleAnnotatorResult


class PipAnnotator(ModuleAnnotator):
    fqcn: str = "ansible.builtin.pip"
    enabled: bool = True

    def run(self, task: TaskCall) -> List[Annotation]:
        pkg = task.args.get("name")
        if pkg is None:
            pkg = task.args.get("requirements")

        annotation = RiskAnnotation.init(risk_type=DefaultRiskType.PACKAGE_INSTALL, detail=PackageInstallDetail(_pkg_arg=pkg))
        return ModuleAnnotatorResult(annotations=[annotation])
