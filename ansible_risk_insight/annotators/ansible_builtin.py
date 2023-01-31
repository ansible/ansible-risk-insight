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

from ansible_risk_insight.models import TaskCall
from ansible_risk_insight.annotators.risk_annotator_base import RiskAnnotator


class AnsibleBuiltinRiskAnnotator(RiskAnnotator):
    name: str = "ansible.builtin"
    enabled: bool = True

    def match(self, task: TaskCall) -> bool:
        resolved_name = task.spec.resolved_name
        return resolved_name.startswith("ansible.builtin.")

    # embed "analyzed_data" field in Task
    def run(self, task: TaskCall):
        if not self.match(task):
            return []

        return self.run_module_annotators("ansible.builtin", task)
