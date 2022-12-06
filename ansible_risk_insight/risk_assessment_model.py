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
from dataclasses import dataclass, field

from .models import LoadType, ObjectList, ExecutableType
from .parser import Parser
from .findings import Findings
from .utils import escape_url, version_to_num
from .safe_glob import safe_glob
from .keyutil import get_obj_info_by_key


@dataclass
class RAMClient(object):
    root_dir: str = ""

    modules_json_list_cache: list = field(default_factory=list)
    roles_json_list_cache: list = field(default_factory=list)
    taskfiles_json_list_cache: list = field(default_factory=list)
    tasks_json_list_cache: list = field(default_factory=list)

    modules_cache: dict = field(default_factory=dict)
    roles_cache: dict = field(default_factory=dict)
    taskfiles_cache: dict = field(default_factory=dict)
    tasks_cache: dict = field(default_factory=dict)

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

    def search_module(self, name, exact_match=False, max_match=-1, collection_name="", collection_version=""):
        if max_match == 0:
            return []
        modules_json_list = []
        if self.modules_json_list_cache:
            modules_json_list = self.modules_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "root", "modules.json")
            modules_json_list = safe_glob(search_patterns)
            modules_json_list = sort_by_version(modules_json_list)
            self.modules_json_list_cache = modules_json_list
        if collection_name != "":
            modules_json_list = [fpath for fpath in modules_json_list if f"/{collection_name}/" in fpath]
        if collection_version != "":
            modules_json_list = [fpath for fpath in modules_json_list if f"/{collection_version}/" in fpath]
        matched_modules = []
        search_end = False
        for modules_json in modules_json_list:
            modules = ObjectList()
            if modules_json in self.modules_cache:
                modules = self.modules_cache[modules_json]
            else:
                modules.from_json(fpath=modules_json)
                self.modules_cache[modules_json] = modules
            for m in modules.items:
                matched = False
                if exact_match:
                    if m.fqcn == name:
                        matched = True
                else:
                    if m.fqcn == name or m.fqcn.endswith(f".{name}"):
                        matched = True
                if matched:
                    parts = modules_json.split("/")

                    matched_modules.append(
                        {
                            "type": "module",
                            "object": m,
                            "collection": {
                                "name": parts[-5],
                                "version": parts[-4],
                                "hash": parts[-3],
                            },
                        }
                    )
                if max_match > 0:
                    if len(matched_modules) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        return matched_modules

    def search_role(self, name, exact_match=False, max_match=-1, collection_name="", collection_version=""):
        if max_match == 0:
            return []
        roles_json_list = []
        if self.roles_json_list_cache:
            roles_json_list = self.roles_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "root", "roles.json")
            roles_json_list = safe_glob(search_patterns)
            roles_json_list = sort_by_version(roles_json_list)
            self.roles_json_list_cache = roles_json_list
        if collection_name != "":
            roles_json_list = [fpath for fpath in roles_json_list if f"/{collection_name}/" in fpath]
        if collection_version != "":
            roles_json_list = [fpath for fpath in roles_json_list if f"/{collection_version}/" in fpath]
        matched_roles = []
        search_end = False
        for roles_json in roles_json_list:
            roles = ObjectList()
            if roles_json in self.roles_cache:
                roles = self.roles_cache[roles_json]
            else:
                roles.from_json(fpath=roles_json)
                self.roles_cache[roles_json] = roles
            for r in roles.items:
                matched = False
                if exact_match:
                    if r.fqcn == name:
                        matched = True
                else:
                    if r.fqcn == name or r.fqcn.endswith(f".{name}"):
                        matched = True
                if matched:
                    parts = roles_json.split("/")
                    offspring_objects = []
                    for taskfile_key in r.taskfiles:
                        _tmp_offspring_objects = self.search_taskfile(taskfile_key, is_key=True, collection_name=r.collection)
                        if len(_tmp_offspring_objects) > 0:
                            tf = _tmp_offspring_objects[0]
                            if tf:
                                offspring_objects.append(tf)
                            offspr_objs = _tmp_offspring_objects[0].get("offspring_objects", [])
                            if offspr_objs:
                                offspring_objects.extend(offspr_objs)
                    matched_roles.append(
                        {
                            "type": "role",
                            "object": r,
                            "offspring_objects": offspring_objects,
                            "collection": {
                                "name": parts[-5],
                                "version": parts[-4],
                                "hash": parts[-3],
                            },
                        }
                    )
                if max_match > 0:
                    if len(matched_roles) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        return matched_roles

    def search_taskfile(self, name, include_task_path="", max_match=-1, is_key=False, collection_name="", collection_version=""):
        if max_match == 0:
            return []
        taskfiles_json_list = []
        if self.taskfiles_json_list_cache:
            taskfiles_json_list = self.taskfiles_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "root", "taskfiles.json")
            taskfiles_json_list = safe_glob(search_patterns)
            taskfiles_json_list = sort_by_version(taskfiles_json_list)
            self.taskfiles_json_list_cache = taskfiles_json_list

        if collection_name != "":
            taskfiles_json_list = [fpath for fpath in taskfiles_json_list if f"/{collection_name}/" in fpath]
        if collection_version != "":
            taskfiles_json_list = [fpath for fpath in taskfiles_json_list if f"/{collection_version}/" in fpath]

        search_path_list = []
        taskfile_ref = name
        if include_task_path != "":
            base_path = os.path.dirname(include_task_path)
            taskfile_path = os.path.normpath(os.path.join(base_path, taskfile_ref))
            search_path_list.append(taskfile_path)
            if "roles/" in taskfile_ref and "roles/" in base_path:
                root_path = base_path.split("roles/")[0]
                taskfile_path = os.path.normpath(os.path.join(root_path, taskfile_ref))
                search_path_list.append(taskfile_path)

        matched_taskfiles = []
        search_end = False
        for taskfiles_json in taskfiles_json_list:
            taskfiles = ObjectList()
            if taskfiles_json in self.taskfiles_cache:
                taskfiles = self.taskfiles_cache[taskfiles_json]
            else:
                taskfiles.from_json(fpath=taskfiles_json)
                self.taskfiles_cache[taskfiles_json] = taskfiles
            for tf in taskfiles.items:
                matched = False
                if is_key:
                    if tf.key == name:
                        matched = True
                else:
                    if tf.defined_in in search_path_list:
                        matched = True
                    # TODO: support taskfile reference with variables
                if matched:
                    parts = taskfiles_json.split("/")
                    offspring_objects = []
                    for task_key in tf.tasks:
                        _tmp_offspring_objects = self.search_task(task_key, is_key=True, collection_name=tf.collection)
                        if len(_tmp_offspring_objects) > 0:
                            t = _tmp_offspring_objects[0]
                            if t:
                                offspring_objects.append(t)
                            offspr_objs = _tmp_offspring_objects[0].get("offspring_objects", [])
                            if offspr_objs:
                                offspring_objects.extend(offspr_objs)

                    matched_taskfiles.append(
                        {
                            "type": "taskfile",
                            "object": tf,
                            "offspring_objects": offspring_objects,
                            "collection": {
                                "name": parts[-5],
                                "version": parts[-4],
                                "hash": parts[-3],
                            },
                        }
                    )
                if max_match > 0:
                    if len(matched_taskfiles) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        return matched_taskfiles

    def search_task(self, name, exact_match=False, max_match=-1, is_key=False, collection_name="", collection_version=""):
        if max_match == 0:
            return []
        tasks_json_list = []
        if self.tasks_json_list_cache:
            tasks_json_list = self.tasks_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "root", "tasks.json")
            tasks_json_list = safe_glob(search_patterns)
            tasks_json_list = sort_by_version(tasks_json_list)
            self.tasks_json_list_cache = tasks_json_list

        if collection_name != "":
            tasks_json_list = [fpath for fpath in tasks_json_list if f"/{collection_name}/" in fpath]
        if collection_version != "":
            tasks_json_list = [fpath for fpath in tasks_json_list if f"/{collection_version}/" in fpath]

        matched_tasks = []
        search_end = False
        for tasks_json in tasks_json_list:
            tasks = ObjectList()
            if tasks_json in self.tasks_cache:
                tasks = self.tasks_cache[tasks_json]
            else:
                tasks.from_json(fpath=tasks_json)
                self.tasks_cache[tasks_json] = tasks
            for t in tasks.items:
                matched = False
                if is_key:
                    if t.key == name:
                        matched = True
                else:
                    if exact_match:
                        if t.name == name:
                            matched = True
                    else:
                        if t.name == name or name in t.name:
                            matched = True
                if matched:
                    parts = tasks_json.split("/")
                    offspring_objects = []
                    if t.executable_type == ExecutableType.MODULE_TYPE:
                        _tmp_offspring_objects = self.search_module(t.executable)
                    elif t.executable_type == ExecutableType.ROLE_TYPE:
                        _tmp_offspring_objects = self.search_role(t.executable)
                    elif t.executable_type == ExecutableType.TASKFILE_TYPE:
                        _tmp_offspring_objects = self.search_taskfile(t.executable, include_task_path=t.defined_in, collection_name=t.collection)
                    if len(_tmp_offspring_objects) > 0:
                        child = _tmp_offspring_objects[0]
                        if child:
                            offspring_objects.append(child)
                        offspr_objs = _tmp_offspring_objects[0].get("offspring_objects", [])
                        if offspr_objs:
                            offspring_objects.extend(offspr_objs)

                    matched_tasks.append(
                        {
                            "type": "task",
                            "object": t,
                            "offspring_objects": offspring_objects,
                            "collection": {
                                "name": parts[-5],
                                "version": parts[-4],
                                "hash": parts[-3],
                            },
                        }
                    )
                if max_match > 0:
                    if len(matched_tasks) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        return matched_tasks

    def get_object_by_key(self, obj_key: str):
        obj_info = get_obj_info_by_key(obj_key)
        obj_type = obj_info.get("type", "")
        parent_name = obj_info.get("parent_name", "")
        type_str = obj_type + "s"

        search_patterns = os.path.join(self.root_dir, "collections", "findings", parent_name, "*", "*", "root", f"{type_str}.json")
        obj_json_list = safe_glob(search_patterns)
        obj_json_list = sort_by_version(obj_json_list)
        matched_obj = None
        for obj_json in obj_json_list:
            objs = ObjectList()
            objs.from_json(fpath=obj_json)
            obj = objs.find_by_key(obj_key)
            if obj is not None:
                parts = obj_json.split("/")
                matched_obj = {
                    "object": obj,
                    "collection": {
                        "name": parts[-5],
                        "version": parts[-4],
                        "hash": parts[-3],
                    },
                }
        return matched_obj

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


def _path_to_version_num(path):
    version = path.split("/findings/")[-1].split("/")[1]
    return version_to_num(version)


def _path_to_collection_name(path):
    collection = path.split("/findings/")[-1].split("/")[0]
    return collection


# the latest known version comes first
# `unknown` is the last
def sort_by_version(path_list):
    return sorted(path_list, key=lambda x: (_path_to_collection_name(x), _path_to_version_num(x)))
