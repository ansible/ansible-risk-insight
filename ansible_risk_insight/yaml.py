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

import io
from contextvars import ContextVar
from ruamel.yaml import YAML


_yaml: ContextVar[YAML] = ContextVar("yaml")


def _set_yaml():
    if not _yaml.get(None):
        _yaml.set(YAML(typ="rt", pure=True))
        _yaml.default_flow_style = False
        _yaml.preserve_quotes = True
        _yaml.allow_duplicate_keys = True


def load(stream: any):
    _set_yaml()
    yaml = _yaml.get()
    return yaml.load(stream)


def dump(data: any):
    _set_yaml()
    yaml = _yaml.get()
    output = io.StringIO()
    yaml.dump(data, output)
    return output.getvalue()
