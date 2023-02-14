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

import traceback
import joblib

from .scanner import ARIScanner, config


class RiskAssessmentModelGenerator(object):
    _queue: list = []
    _resume: int = -1
    _update: bool = False

    def __init__(self, target_list=[], resume=-1, update=False, parallel=True, download_only=False, no_module_spec=False):
        self._queue = target_list
        self._resume = resume
        self._update = update
        self._parallel = parallel
        self._download_only = download_only
        self._no_module_spec = no_module_spec

        use_ansible_doc = True
        if self._no_module_spec:
            use_ansible_doc = False

        self._scanner = ARIScanner(
            root_dir=config.data_dir,
            silent=True,
            use_ansible_doc=use_ansible_doc,
        )

    def run(self):
        num = len(self._queue)
        resume_str = f"(resume from {self._resume})" if self._resume > 0 else ""
        print(f"Start scanning {num} targets {resume_str}")

        input_list = []
        for i, target_info in enumerate(self._queue):
            if i + 1 < self._resume:
                continue
            if not isinstance(target_info, tuple):
                raise ValueError(f"target list must be a list of tuple(target_type, target_name), but got a {type(target_info)}")
            if len(target_info) != 2:
                raise ValueError(f"target list must be a list of tuple(target_type, target_name), but got this; {target_info}")

            _type, _name = target_info
            input_list.append((i, num, _type, _name))

        if self._parallel:
            joblib.Parallel(n_jobs=-1)(joblib.delayed(self.scan)(i, num, _type, _name) for (i, num, _type, _name) in input_list)
        else:
            for (i, num, _type, _name) in input_list:
                self.scan(i, num, _type, _name)

    def scan(self, i, num, type, name):
        print(f"[{i+1}/{num}] {type} {name}")
        use_src_cache = True
        if self._update:
            # disable dependency cache when update mode to avoid using the old src
            use_src_cache = False
        try:

            self._scanner.evaluate(
                type=type,
                name=name,
                install_dependencies=True,
                download_only=self._download_only,
                use_src_cache=use_src_cache,
            )
        except Exception:
            error = traceback.format_exc()
            self._scanner.save_error(error)
