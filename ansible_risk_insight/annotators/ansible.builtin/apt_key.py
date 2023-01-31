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
from ansible_risk_insight.models import Annotation, RiskAnnotation, TaskCall, DefaultRiskType, KeyConfigChangeDetail
from ansible_risk_insight.annotators.module_annotator_base import ModuleAnnotator, ModuleAnnotatorResult


class AptKeyAnnotator(ModuleAnnotator):
    fqcn: str = "ansible.builtin.apt_key"
    enabled: bool = True

    def run(self, task: TaskCall) -> List[Annotation]:
        # id = task.args.get("id")
        key = None
        if key is None:
            key = task.args.get("url")
        if key is None:
            key = task.args.get("data")
        if key is None:
            key = task.args.get("keyserver")

        state = task.args.get("state")

        annotation = RiskAnnotation.init(risk_type=DefaultRiskType.CONFIG_CHANGE,
                                         detail=KeyConfigChangeDetail(_key_arg=key, _state_arg=state))
        return ModuleAnnotatorResult(annotations=[annotation])
