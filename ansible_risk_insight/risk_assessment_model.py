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

import os
import json
from dataclasses import dataclass

from .models import LoadType
from .parser import Parser
from .findings import Findings
from .utils import escape_url


@dataclass
class RAMClient(object):
    root_dir: str = ""

    def register(self, findings: Findings):
        metadata = findings.metadata

        type = metadata.get("type", "")
        name = metadata.get("name", "")
        version = metadata.get("version", "")
        hash = metadata.get("hash", "")

        out_dir = self.make_findings_dir_path(type, name, version, hash)
        self.save_findings(findings, out_dir)

    def make_findings_dir_path(self, type, name, version, hash):
        type_root = type + "s"
        dir_name = name
        if type == LoadType.PROJECT:
            dir_name = escape_url(name)
        ver_str = version if version != "" else "unknown"
        hash_str = hash if hash != "" else "unknown"
        out_dir = os.path.join(self.root_dir, type_root, "findings", dir_name, ver_str, hash_str)
        return out_dir

    def load_definitions_from_findings(self, type, name, version, hash):
        findings_dir = self.make_findings_dir_path(type, name, version, hash)
        defs_dir = os.path.join(findings_dir, "root")
        loaded = False
        definitions = {}
        mappings = {}
        if os.path.exists(defs_dir):
            definitions, mappings = Parser.restore_definition_objects(defs_dir)
            loaded = True
        return loaded, definitions, mappings

    def save_findings(self, findings: Findings, out_dir: str):
        if out_dir == "":
            raise ValueError("output dir must be a non-empty value")

        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        root_defs_dir = os.path.join(out_dir, "root")
        if not os.path.exists(root_defs_dir):
            os.makedirs(root_defs_dir, exist_ok=True)

        if len(findings.root_definitions) > 0:
            root_definitions = findings.root_definitions["definitions"]
            root_mappings = findings.root_definitions["mappings"]
            Parser.dump_definition_objects(root_defs_dir, root_definitions, root_mappings)

        ext_defs_base_dir = os.path.join(out_dir, "ext")
        if not os.path.exists(ext_defs_base_dir):
            os.makedirs(ext_defs_base_dir, exist_ok=True)

        if len(findings.ext_definitions) > 0:
            for key in findings.ext_definitions:
                ext_definitions = findings.ext_definitions[key]["definitions"]
                ext_mappings = findings.ext_definitions[key]["mappings"]
                ext_defs_dir = os.path.join(ext_defs_base_dir, key)
                if not os.path.exists(ext_defs_dir):
                    os.makedirs(ext_defs_dir, exist_ok=True)
                Parser.dump_definition_objects(ext_defs_dir, ext_definitions, ext_mappings)

        findings_path = os.path.join(out_dir, "findings.json")
        with open(findings_path, "w") as findings_file:
            json.dump(findings.report, findings_file)

        metadata_path = os.path.join(out_dir, "metadata.json")
        with open(metadata_path, "w") as metadata_file:
            json.dump(findings.metadata, metadata_file)

        dependencies_path = os.path.join(out_dir, "dependencies.json")
        with open(dependencies_path, "w") as dependencies_file:
            json.dump(findings.dependencies, dependencies_file)

        prm_file = os.path.join(out_dir, "prm.json")
        with open(prm_file, "w") as prm:
            json.dump(findings.prm, prm)
