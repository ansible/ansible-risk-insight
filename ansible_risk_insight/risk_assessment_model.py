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
import jsonpickle
from dataclasses import dataclass, field
import tarfile

from .models import (
    LoadType,
    ObjectList,
    ExecutableType,
    Module,
    ModuleMetadata,
)
from .findings import Findings
from .utils import escape_url, version_to_num, diff_files_data
from .safe_glob import safe_glob
from .keyutil import get_obj_info_by_key
from .model_loader import load_builtin_modules


module_index_name = "module_index.json"


@dataclass
class RAMClient(object):
    root_dir: str = ""

    findings_json_list_cache: list = field(default_factory=list)
    modules_json_list_cache: list = field(default_factory=list)
    roles_json_list_cache: list = field(default_factory=list)
    taskfiles_json_list_cache: list = field(default_factory=list)
    tasks_json_list_cache: list = field(default_factory=list)

    modules_cache: dict = field(default_factory=dict)
    roles_cache: dict = field(default_factory=dict)
    taskfiles_cache: dict = field(default_factory=dict)
    tasks_cache: dict = field(default_factory=dict)

    module_search_cache: dict = field(default_factory=dict)
    task_search_cache: dict = field(default_factory=dict)

    builtin_modules_cache: dict = field(default_factory=dict)

    module_index: dict = field(default_factory=dict)

    def __post_init__(self):
        module_index_path = os.path.join(self.root_dir, "indices", module_index_name)
        if os.path.exists(module_index_path):
            with open(module_index_path, "r") as file:
                self.module_index = json.load(file)

    def register(self, findings: Findings):
        metadata = findings.metadata

        type = metadata.get("type", "")
        name = metadata.get("name", "")
        version = metadata.get("version", "")
        hash = metadata.get("hash", "")

        out_dir = self.make_findings_dir_path(type, name, version, hash)
        self.save_findings(findings, out_dir)

    def module_index_register(self, findings: Findings):
        modules = self.load_module_index()
        for module in findings.root_definitions.get("definitions", {}).get("modules", []):
            if not isinstance(module, Module):
                continue
            m_meta = ModuleMetadata.from_module(module, findings.metadata)
            current = modules.get(module.name, [])
            if m_meta not in current:
                current.append(m_meta)
            modules.update({module.name: current})
        self.save_module_index(modules)

    def make_findings_dir_path(self, type, name, version, hash):
        type_root = type + "s"
        dir_name = name
        if type in [LoadType.PROJECT, LoadType.PLAYBOOK, LoadType.TASKFILE]:
            dir_name = escape_url(name)
        ver_str = version if version != "" else "unknown"
        hash_str = hash if hash != "" else "unknown"
        out_dir = os.path.join(self.root_dir, type_root, "findings", dir_name, ver_str, hash_str)
        return out_dir

    def load_metadata_from_findings(self, type, name, version, hash="*"):
        findings = self.search_findings(name, version, type)
        if not findings:
            return False, None, None
        if not isinstance(findings, Findings):
            return False, None, None
        return True, findings.metadata, findings.dependencies

    def load_definitions_from_findings(self, type, name, version, hash, allow_unresolved=False):
        findings_dir = self.make_findings_dir_path(type, name, version, hash)
        findings_path = os.path.join(findings_dir, "findings.json")
        loaded = False
        definitions = {}
        mappings = {}
        if os.path.exists(findings_path):
            findings = Findings.load(fpath=findings_path)
            # use RAM only if no unresolved dependency
            # (RAM should be fully-resolved specs as much as possible)
            if findings and (len(findings.extra_requirements) == 0 or allow_unresolved):
                definitions = findings.root_definitions.get("definitions", {})
                mappings = findings.root_definitions.get("mappings", {})
                if mappings:
                    loaded = True
        return loaded, definitions, mappings

    def search_builtin_module(self, name, used_in=""):
        builtin_modules = {}
        if self.builtin_modules_cache:
            builtin_modules = self.builtin_modules_cache
        else:
            builtin_modules = load_builtin_modules()
            self.builtin_modules_cache = builtin_modules
        short_name = name
        if "ansible.builtin." in name:
            short_name = name.split(".")[-1]
        matched_modules = []
        if short_name in builtin_modules:
            m = builtin_modules[short_name]
            matched_modules.append(
                {
                    "type": "module",
                    "name": m.fqcn,
                    "object": m,
                    "defined_in": {
                        "type": "collection",
                        "name": m.collection,
                        "version": "unknown",
                        "hash": "unknown",
                    },
                    "used_in": used_in,
                }
            )
        return matched_modules

    def load_from_indice(self, short_name, meta, used_in=""):
        _type = meta.get("type", "")
        _name = meta.get("name", "")
        collection = ""
        role = ""
        if _type == "collection":
            collection = _name
        elif _type == "role":
            role = _name
        _version = meta.get("version", "")
        _hash = meta.get("hash", "")
        m = Module(
            name=short_name,
            fqcn=meta.get("fqcn", ""),
            collection=collection,
            role=role,
        )
        m_wrapper = {
            "type": "module",
            "name": m.fqcn,
            "object": m,
            "defined_in": {
                "type": m.type,
                "name": _name,
                "version": _version,
                "hash": _hash,
            },
            "used_in": used_in,
        }
        return m_wrapper

    def search_module(self, name, exact_match=False, max_match=-1, collection_name="", collection_version="", used_in=""):
        if max_match == 0:
            return []
        args_str = json.dumps([name, exact_match, max_match, collection_name, collection_version])
        if args_str in self.module_search_cache:
            return self.module_search_cache[args_str]

        # check if the module is builtin
        matched_builtin_modules = self.search_builtin_module(name, used_in)
        if len(matched_builtin_modules) > 0:
            self.module_search_cache[args_str] = matched_builtin_modules
            return matched_builtin_modules

        short_name = name
        if "." in name:
            short_name = name.split(".")[-1]

        from_indices = False
        found_index = None
        if short_name in self.module_index and self.module_index[short_name]:
            from_indices = True
            found_index = self.module_index[short_name][0]

        modules_json_list = []
        if from_indices:
            _type = found_index.get("type", "")
            _name = found_index.get("name", "")
            _version = found_index.get("version", "")
            _hash = found_index.get("hash", "")
            findings_path = os.path.join(self.root_dir, _type + "s", "findings", _name, _version, _hash, "findings.json")
            if os.path.exists(findings_path):
                modules_json_list.append(findings_path)
        else:
            # Do not search a module from all findings
            # when it is not found in the module index.
            # Instead, just return nothing in the case.
            pass
        matched_modules = []
        search_end = False
        for findings_json in modules_json_list:
            modules = ObjectList()
            if findings_json in self.modules_cache:
                modules = self.modules_cache[findings_json]
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                modules = f.root_definitions.get("definitions", {}).get("modules", [])
                self.modules_cache[findings_json] = modules
            for m in modules:
                matched = False
                if exact_match:
                    if m.fqcn == name:
                        matched = True
                else:
                    if m.fqcn == name or m.fqcn.endswith(f".{name}"):
                        matched = True
                if matched:
                    parts = findings_json.split("/")

                    matched_modules.append(
                        {
                            "type": "module",
                            "name": m.fqcn,
                            "object": m,
                            "defined_in": {
                                "type": parts[-6][:-1],  # collection or role
                                "name": parts[-4],
                                "version": parts[-3],
                                "hash": parts[-2],
                            },
                            "used_in": used_in,
                        }
                    )
                if max_match > 0:
                    if len(matched_modules) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        self.module_search_cache[args_str] = matched_modules
        return matched_modules

    def search_role(self, name, exact_match=False, max_match=-1, collection_name="", collection_version="", used_in=""):
        if max_match == 0:
            return []
        findings_json_list = []
        if self.findings_json_list_cache:
            findings_json_list = self.findings_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "findings.json")
            findings_json_list_coll = safe_glob(search_patterns)
            findings_json_list_coll = sort_by_version(findings_json_list_coll)
            search_patterns = os.path.join(self.root_dir, "roles", "findings", "*", "*", "*", "findings.json")
            findings_json_list_role = safe_glob(search_patterns)
            findings_json_list_role = sort_by_version(findings_json_list_role)
            findings_json_list = findings_json_list_coll + findings_json_list_role
            self.findings_json_list_cache = findings_json_list

        roles_json_list = []
        if self.roles_json_list_cache:
            roles_json_list = self.roles_json_list_cache
        else:
            for findings_json in findings_json_list:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                # avoid using unresolved RAM data
                if f.extra_requirements:
                    continue
                roles = f.root_definitions.get("definitions", {}).get("roles", [])
                self.roles_cache[findings_json] = roles
                roles_json_list.append(findings_json)
            self.roles_json_list_cache = roles_json_list

        if collection_name != "":
            roles_json_list = [fpath for fpath in roles_json_list if f"/{collection_name}/" in fpath]
        if collection_version != "":
            roles_json_list = [fpath for fpath in roles_json_list if f"/{collection_version}/" in fpath]

        matched_roles = []
        search_end = False
        for findings_json in roles_json_list:
            roles = ObjectList()
            if findings_json in self.roles_cache:
                roles = self.roles_cache[findings_json]
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                roles = f.root_definitions.get("definitions", {}).get("roles", [])
                self.roles_cache[findings_json] = roles
            for r in roles:
                matched = False
                if exact_match:
                    if r.fqcn == name:
                        matched = True
                else:
                    if r.fqcn == name or r.fqcn.endswith(f".{name}"):
                        matched = True
                if matched:
                    parts = findings_json.split("/")
                    offspring_objects = []
                    for taskfile_key in r.taskfiles:
                        _tmp_offspring_objects = self.search_taskfile(taskfile_key, is_key=True, collection_name=r.collection)
                        if len(_tmp_offspring_objects) > 0:
                            tf = _tmp_offspring_objects[0]
                            if tf:
                                offspring_objects.append(tf)
                            offspr_objs = _tmp_offspring_objects[0].get("offspring_objects", [])
                            if offspr_objs:
                                _offspring_obj_set = set()
                                for offspr_obj in offspr_objs:
                                    _offspr_obj_instance = offspr_obj.get("object", None)
                                    if _offspr_obj_instance is None:
                                        continue
                                    if _offspr_obj_instance.key not in _offspring_obj_set:
                                        offspring_objects.append(offspr_obj)
                                        _offspring_obj_set.add(_offspr_obj_instance.key)
                    matched_roles.append(
                        {
                            "type": "role",
                            "name": r.fqcn,
                            "object": r,
                            "offspring_objects": offspring_objects,
                            "defined_in": {
                                "type": parts[-5][:-1],  # collection or role
                                "name": parts[-4],
                                "version": parts[-3],
                                "hash": parts[-2],
                            },
                            "used_in": used_in,
                        }
                    )
                if max_match > 0:
                    if len(matched_roles) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        return matched_roles

    def search_taskfile(self, name, include_task_path="", max_match=-1, is_key=False, collection_name="", collection_version="", used_in=""):
        if max_match == 0:
            return []
        findings_json_list = []
        if self.findings_json_list_cache:
            findings_json_list = self.findings_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "findings.json")
            findings_json_list_coll = safe_glob(search_patterns)
            findings_json_list_coll = sort_by_version(findings_json_list_coll)
            search_patterns = os.path.join(self.root_dir, "roles", "findings", "*", "*", "*", "findings.json")
            findings_json_list_role = safe_glob(search_patterns)
            findings_json_list_role = sort_by_version(findings_json_list_role)
            findings_json_list = findings_json_list_coll + findings_json_list_role
            self.findings_json_list_cache = findings_json_list

        taskfiles_json_list = []
        if self.taskfiles_json_list_cache:
            taskfiles_json_list = self.taskfiles_json_list_cache
        else:
            for findings_json in findings_json_list:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                # avoid using unresolved RAM data
                if f.extra_requirements:
                    continue
                taskfiles = f.root_definitions.get("definitions", {}).get("taskfiles", [])
                self.taskfiles_cache[findings_json] = taskfiles
                taskfiles_json_list.append(findings_json)
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
        for findings_json in taskfiles_json_list:
            taskfiles = ObjectList()
            if findings_json in self.taskfiles_cache:
                taskfiles = self.taskfiles_cache[findings_json]
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                taskfiles = f.root_definitions.get("definitions", {}).get("taskfiles", [])
                self.taskfiles_cache[findings_json] = taskfiles
            for tf in taskfiles:
                matched = False
                if is_key:
                    if tf.key == name:
                        matched = True
                else:
                    if tf.defined_in in search_path_list:
                        matched = True
                    # TODO: support taskfile reference with variables
                if matched:
                    parts = findings_json.split("/")
                    offspring_objects = []
                    for task_key in tf.tasks:
                        _tmp_offspring_objects = self.search_task(task_key, is_key=True, collection_name=tf.collection, used_in=used_in)
                        if len(_tmp_offspring_objects) > 0:
                            t = _tmp_offspring_objects[0]
                            if t:
                                offspring_objects.append(t)
                            offspr_objs = _tmp_offspring_objects[0].get("offspring_objects", [])
                            if offspr_objs:
                                _offspring_obj_set = set()
                                for offspr_obj in offspr_objs:
                                    _offspr_obj_instance = offspr_obj.get("object", None)
                                    if _offspr_obj_instance is None:
                                        continue
                                    if _offspr_obj_instance.key not in _offspring_obj_set:
                                        offspring_objects.append(offspr_obj)
                                        _offspring_obj_set.add(_offspr_obj_instance.key)

                    matched_taskfiles.append(
                        {
                            "type": "taskfile",
                            "name": tf.key,
                            "object": tf,
                            "offspring_objects": offspring_objects,
                            "defined_in": {
                                "type": parts[-5][:-1],  # collection or role
                                "name": parts[-4],
                                "version": parts[-3],
                                "hash": parts[-2],
                            },
                            "used_in": used_in,
                        }
                    )
                if max_match > 0:
                    if len(matched_taskfiles) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        return matched_taskfiles

    def search_task(self, name, exact_match=False, max_match=-1, is_key=False, collection_name="", collection_version="", used_in=""):
        if max_match == 0:
            return []
        args_str = json.dumps([name, exact_match, max_match, is_key, collection_name, collection_version])
        if args_str in self.task_search_cache:
            return self.task_search_cache[args_str]
        findings_json_list = []
        if self.findings_json_list_cache:
            findings_json_list = self.findings_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "findings.json")
            findings_json_list_coll = safe_glob(search_patterns)
            findings_json_list_coll = sort_by_version(findings_json_list_coll)
            search_patterns = os.path.join(self.root_dir, "roles", "findings", "*", "*", "*", "findings.json")
            findings_json_list_role = safe_glob(search_patterns)
            findings_json_list_role = sort_by_version(findings_json_list_role)
            findings_json_list = findings_json_list_coll + findings_json_list_role
            self.findings_json_list_cache = findings_json_list

        tasks_json_list = []
        if self.tasks_json_list_cache:
            tasks_json_list = self.tasks_json_list_cache
        else:
            for findings_json in findings_json_list:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                # avoid using unresolved RAM data
                if f.extra_requirements:
                    continue
                tasks = f.root_definitions.get("definitions", {}).get("tasks", [])
                self.tasks_cache[findings_json] = tasks
                tasks_json_list.append(findings_json)
            self.tasks_json_list_cache = tasks_json_list

        if collection_name != "":
            tasks_json_list = [fpath for fpath in tasks_json_list if f"/{collection_name}/" in fpath]
        if collection_version != "":
            tasks_json_list = [fpath for fpath in tasks_json_list if f"/{collection_version}/" in fpath]

        matched_tasks = []
        search_end = False
        for findings_json in tasks_json_list:
            tasks = ObjectList()
            if findings_json in self.tasks_cache:
                tasks = self.tasks_cache[findings_json]
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                tasks = f.root_definitions.get("definitions", {}).get("tasks", [])
                self.tasks_cache[findings_json] = tasks
            for t in tasks:
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
                    parts = findings_json.split("/")
                    offspring_objects = []
                    if t.executable_type == ExecutableType.MODULE_TYPE:
                        _tmp_offspring_objects = self.search_module(t.executable, used_in=t.defined_in)
                    elif t.executable_type == ExecutableType.ROLE_TYPE:
                        _tmp_offspring_objects = self.search_role(t.executable, used_in=t.defined_in)
                    elif t.executable_type == ExecutableType.TASKFILE_TYPE:
                        _tmp_offspring_objects = self.search_taskfile(
                            t.executable, include_task_path=t.defined_in, collection_name=t.collection, used_in=t.defined_in
                        )
                    if len(_tmp_offspring_objects) > 0:
                        child = _tmp_offspring_objects[0]
                        if child:
                            offspring_objects.append(child)
                        offspr_objs = _tmp_offspring_objects[0].get("offspring_objects", [])
                        if offspr_objs:
                            _offspring_obj_set = set()
                            for offspr_obj in offspr_objs:
                                _offspr_obj_instance = offspr_obj.get("object", None)
                                if _offspr_obj_instance is None:
                                    continue
                                if _offspr_obj_instance.key not in _offspring_obj_set:
                                    offspring_objects.append(offspr_obj)
                                    _offspring_obj_set.add(_offspr_obj_instance.key)

                    matched_tasks.append(
                        {
                            "type": "task",
                            "name": t.key,
                            "object": t,
                            "offspring_objects": offspring_objects,
                            "defined_in": {
                                "type": parts[-5][:-1],  # collection or role
                                "name": parts[-4],
                                "version": parts[-3],
                                "hash": parts[-2],
                            },
                            "used_in": used_in,
                        }
                    )
                if max_match > 0:
                    if len(matched_tasks) >= max_match:
                        search_end = True
                        break
            if search_end:
                break
        self.task_search_cache[args_str] = matched_tasks
        return matched_tasks

    def get_object_by_key(self, obj_key: str):
        obj_info = get_obj_info_by_key(obj_key)
        obj_type = obj_info.get("type", "")
        parent_name = obj_info.get("parent_name", "")
        type_str = obj_type + "s"

        search_patterns = os.path.join(self.root_dir, "collections", "findings", parent_name, "*", "*", "root", f"{type_str}.json")
        obj_json_list_coll = safe_glob(search_patterns)
        obj_json_list_coll = sort_by_version(obj_json_list_coll)
        search_patterns = os.path.join(self.root_dir, "roles", "findings", parent_name, "*", "*", "root", f"{type_str}.json")
        obj_json_list_role = safe_glob(search_patterns)
        obj_json_list_role = sort_by_version(obj_json_list_role)
        obj_json_list = obj_json_list_coll + obj_json_list_role

        matched_obj = None
        for obj_json in obj_json_list:
            objs = ObjectList.from_json(fpath=obj_json)
            obj = objs.find_by_key(obj_key)
            if obj is not None:
                parts = obj_json.split("/")
                matched_obj = {
                    "object": obj,
                    "defined_in": {
                        "type": parts[-6][:-1],  # collection or role
                        "name": parts[-5],
                        "version": parts[-4],
                        "hash": parts[-3],
                    },
                }
        return matched_obj

    def list_all_ram_metadata(self):
        findings_json_list = []
        if self.findings_json_list_cache:
            findings_json_list = self.findings_json_list_cache
        else:
            search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "findings.json")
            findings_json_list_coll = safe_glob(search_patterns)
            findings_json_list_coll = sort_by_version(findings_json_list_coll)
            search_patterns = os.path.join(self.root_dir, "roles", "findings", "*", "*", "*", "findings.json")
            findings_json_list_role = safe_glob(search_patterns)
            findings_json_list_role = sort_by_version(findings_json_list_role)
            findings_json_list = findings_json_list_coll + findings_json_list_role
            self.findings_json_list_cache = findings_json_list

        metadata_list = []
        for findings_path in findings_json_list:
            parts = findings_path.split("/")

            metadata_list.append(
                {
                    "type": parts[-5][:-1],  # collection or role
                    "name": parts[-4],
                    "version": parts[-3],
                    "hash": parts[-2],
                }
            )
        return metadata_list

    def search_findings(self, target_name, target_version, target_type=None):
        if not target_name:
            raise ValueError("target name must be specified for searching RAM data")
        if not target_version:
            target_version = "*"
        search_patterns = []
        if not target_type or target_type == "collection":
            search_patterns.append(os.path.join(self.root_dir, "collections", "findings", target_name, target_version, "*", "findings.json"))
        if not target_type or target_type == "role":
            search_patterns.append(os.path.join(self.root_dir, "roles", "findings", target_name, target_version, "*", "findings.json"))
        if not target_type or target_type == "project":
            e_target_name = escape_url(target_name)
            search_patterns.append(os.path.join(self.root_dir, "projects", "findings", e_target_name, target_version, "*", "findings.json"))
        if not target_type or target_type == "playbook":
            e_target_name = escape_url(target_name)
            search_patterns.append(os.path.join(self.root_dir, "playbooks", "findings", e_target_name, target_version, "*", "findings.json"))
        if not target_type or target_type == "taskfile":
            e_target_name = escape_url(target_name)
            search_patterns.append(os.path.join(self.root_dir, "taskfiles", "findings", e_target_name, target_version, "*", "findings.json"))
        found_path_list = safe_glob(search_patterns)
        latest_findings_path = ""
        if len(found_path_list) == 1:
            latest_findings_path = found_path_list[0]
        elif len(found_path_list) > 1:
            latest_findings_path = found_path_list[0]
            mtime = os.path.getmtime(latest_findings_path)
            for fpath in found_path_list:
                tmp_mtime = os.path.getmtime(fpath)
                if tmp_mtime > mtime:
                    latest_findings_path = fpath
                    mtime = tmp_mtime
        findings = None
        if os.path.exists(latest_findings_path):
            findings = self.load_findings(latest_findings_path)
        return findings

    def load_findings(self, path: str):

        basename = os.path.basename(path)
        dir_path = path
        if basename == "findings.json":
            dir_path = os.path.dirname(path)

        findings = Findings.load(fpath=os.path.join(dir_path, "findings.json"))
        return findings

    def save_findings(self, findings: Findings, out_dir: str):
        if out_dir == "":
            raise ValueError("output dir must be a non-empty value")

        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        findings.dump(fpath=os.path.join(out_dir, "findings.json"))

    def save_module_index(self, modules):
        out_dir = os.path.join(self.root_dir, "indices")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        modules_str = jsonpickle.encode(modules, make_refs=False, unpicklable=False)
        with open(os.path.join(out_dir, "module_index.json"), "w") as file:
            file.write(modules_str)

    def load_module_index(self):
        path = os.path.join(self.root_dir, "indices", "module_index.json")
        modules = {}
        if os.path.exists(path):
            with open(path, "r") as file:
                modules = json.load(file)
        return modules

    def save_error(self, error: str, out_dir: str):
        if out_dir == "":
            raise ValueError("output dir must be a non-empty value")

        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        with open(os.path.join(out_dir, "error.log"), "w") as file:
            file.write(error)

    def diff(self, target_name, version1, version2):
        findings1 = self.search_findings(target_name=target_name, target_version=version1)
        if not findings1:
            raise ValueError(f"{target_name}:{version1} is not found in RAM")

        findings2 = self.search_findings(target_name=target_name, target_version=version2)
        if not findings2:
            raise ValueError(f"{target_name}:{version2} is not found in RAM")

        coll_defs1 = findings1.root_definitions.get("definitions", {}).get("collections", [])
        coll_defs2 = findings2.root_definitions.get("definitions", {}).get("collections", [])

        files1 = None
        files2 = None
        if len(coll_defs1) > 0:
            files1 = coll_defs1[0].files
        if len(coll_defs2) > 0:
            files2 = coll_defs2[0].files

        if not files1:
            raise ValueError(f"Files data of {target_name}:{version1} is not recorded")

        if not files2:
            raise ValueError(f"Files data of {target_name}:{version2} is not recorded")

        return diff_files_data(files1, files2)

    def release(self, outfile):
        indices = os.path.join(self.root_dir, "indices")
        collection_findings = os.path.join(self.root_dir, "collections", "findings")
        role_findings = os.path.join(self.root_dir, "roles", "findings")
        with tarfile.open(outfile, 'w:gz') as tar:
            if os.path.exists(indices):
                tar.add(indices, arcname="indices")
            if os.path.exists(collection_findings):
                tar.add(collection_findings, arcname="collections/findings")
            if os.path.exists(role_findings):
                tar.add(role_findings, arcname="roles/findings")


# newer version comes earlier, so version num should be sorted in a reversed order
def _path_to_reversed_version_num(path):
    version = path.split("/findings/")[-1].split("/")[1]
    return -1 * version_to_num(version)


def _path_to_collection_name(path):
    collection = path.split("/findings/")[-1].split("/")[0]
    return collection


# the latest known version comes first
# `unknown` is the last
def sort_by_version(path_list):
    return sorted(path_list, key=lambda x: (_path_to_collection_name(x), _path_to_reversed_version_num(x)))
