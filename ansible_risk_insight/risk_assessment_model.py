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
    Collection,
    Module,
    ModuleMetadata,
    Role,
    RoleMetadata,
    TaskFile,
    TaskFileMetadata,
    ActionGroupMetadata,
)
from .findings import Findings
from .utils import (
    escape_url,
    version_to_num,
    diff_files_data,
    is_test_object,
    lock_file,
    unlock_file,
    remove_lock_file,
)
from .safe_glob import safe_glob
from .keyutil import get_obj_info_by_key, make_imported_taskfile_key
from .model_loader import load_builtin_modules


module_index_name = "module_index.json"
role_index_name = "role_index.json"
taskfile_index_name = "taskfile_index.json"
action_group_index_name = "action_group_index.json"


@dataclass
class RAMClient(object):
    root_dir: str = ""

    findings_json_list_cache: list = field(default_factory=list)

    findings_cache: dict = field(default_factory=dict)
    findings_search_cache: dict = field(default_factory=dict)

    module_search_cache: dict = field(default_factory=dict)
    role_search_cache: dict = field(default_factory=dict)
    taskfile_search_cache: dict = field(default_factory=dict)
    task_search_cache: dict = field(default_factory=dict)

    builtin_modules_cache: dict = field(default_factory=dict)

    module_index: dict = field(default_factory=dict)
    role_index: dict = field(default_factory=dict)
    taskfile_index: dict = field(default_factory=dict)

    # used for grouped module_defaults such as `group/aws`
    action_group_index: dict = field(default_factory=dict)

    max_cache_size: int = 200

    def __post_init__(self):
        module_index_path = os.path.join(self.root_dir, "indices", module_index_name)
        if os.path.exists(module_index_path):
            with open(module_index_path, "r") as file:
                self.module_index = json.load(file)

        role_index_path = os.path.join(self.root_dir, "indices", role_index_name)
        if os.path.exists(role_index_path):
            with open(role_index_path, "r") as file:
                self.role_index = json.load(file)

        taskfile_index_path = os.path.join(self.root_dir, "indices", taskfile_index_name)
        if os.path.exists(taskfile_index_path):
            with open(taskfile_index_path, "r") as file:
                self.taskfile_index = json.load(file)

        action_group_index_path = os.path.join(self.root_dir, "indices", action_group_index_name)
        if os.path.exists(action_group_index_path):
            with open(action_group_index_path, "r") as file:
                self.action_group_index = json.load(file)

    def clear_old_cache(self):
        size = self.max_cache_size
        self._remove_old_item(self.findings_cache, size)
        self._remove_old_item(self.findings_search_cache, size)
        self._remove_old_item(self.module_search_cache, size)
        self._remove_old_item(self.role_search_cache, size)
        self._remove_old_item(self.taskfile_search_cache, size)
        self._remove_old_item(self.task_search_cache, size)
        return

    def _remove_old_item(self, data: dict, size: int):
        if len(data) <= size:
            return
        num = len(data) - size
        for _ in range(num):
            oldest_key = next(iter(data))
            data.pop(oldest_key)
        return

    def register(self, findings: Findings):
        metadata = findings.metadata

        type = metadata.get("type", "")
        name = metadata.get("name", "")
        version = metadata.get("version", "")
        hash = metadata.get("hash", "")

        out_dir = self.make_findings_dir_path(type, name, version, hash)
        self.save_findings(findings, out_dir)

        self.clear_old_cache()

    def register_indices_to_ram(self, findings: Findings, include_test_contents: bool = False):
        self.register_module_index_to_ram(findings=findings, include_test_contents=include_test_contents)
        self.register_role_index_to_ram(findings=findings, include_test_contents=include_test_contents)
        self.register_taskfile_index_to_ram(findings=findings, include_test_contents=include_test_contents)
        self.register_action_group_index_to_ram(findings=findings)

    def register_module_index_to_ram(self, findings: Findings, include_test_contents: bool = False):
        new_data_found = False
        modules = self.load_module_index()
        for module in findings.root_definitions.get("definitions", {}).get("modules", []):
            if not isinstance(module, Module):
                continue
            if include_test_contents and is_test_object(module.defined_in):
                continue
            m_meta = ModuleMetadata.from_module(module, findings.metadata)
            current = modules.get(module.name, [])
            exists = False
            for m_dict in current:
                m = None
                if isinstance(m_dict, dict):
                    m = ModuleMetadata.from_dict(m_dict)
                elif isinstance(m_dict, ModuleMetadata):
                    m = m_dict
                if not m:
                    continue
                if m == m_meta:
                    exists = True
                    break
            if not exists:
                current.append(m_meta)
                new_data_found = True
            modules.update({module.name: current})
        for collection in findings.root_definitions.get("definitions", {}).get("collections", []):
            if not isinstance(collection, Collection):
                continue
            if collection.meta_runtime and isinstance(collection.meta_runtime, dict):
                for short_name, routing in collection.meta_runtime.get("plugin_routing", {}).get("modules", {}).items():
                    redirect_to = routing.get("redirect", "")
                    if not redirect_to:
                        continue
                    m_meta = ModuleMetadata.from_routing(redirect_to, findings.metadata)
                    current = modules.get(short_name, [])
                    exists = False
                    for m_dict in current:
                        m = None
                        if isinstance(m_dict, dict):
                            m = ModuleMetadata.from_dict(m_dict)
                        elif isinstance(m_dict, ModuleMetadata):
                            m = m_dict
                        if not m:
                            continue
                        if m == m_meta:
                            exists = True
                            break
                    if not exists:
                        current.append(m_meta)
                        new_data_found = True
                    modules.update({short_name: current})
        if new_data_found:
            self.save_module_index(modules)
        return

    def register_role_index_to_ram(self, findings: Findings, include_test_contents: bool = False):
        new_data_found = False
        roles = self.load_role_index()
        for role in findings.root_definitions.get("definitions", {}).get("roles", []):
            if not isinstance(role, Role):
                continue
            if include_test_contents and is_test_object(role.defined_in):
                continue
            r_meta = RoleMetadata.from_role(role, findings.metadata)
            current = roles.get(r_meta.fqcn, [])
            exists = False
            for r_dict in current:
                r = None
                if isinstance(r_dict, dict):
                    r = RoleMetadata.from_dict(r_dict)
                elif isinstance(r_dict, RoleMetadata):
                    r = r_dict
                if not r:
                    continue
                if r == r_meta:
                    exists = True
                    break
            if not exists:
                current.append(r_meta)
                new_data_found = True
            roles.update({role.fqcn: current})
        if new_data_found:
            self.save_role_index(roles)
        return

    def register_taskfile_index_to_ram(self, findings: Findings, include_test_contents: bool = False):
        new_data_found = False
        taskfiles = self.load_taskfile_index()
        for taskfile in findings.root_definitions.get("definitions", {}).get("taskfiles", []):
            if not isinstance(taskfile, TaskFile):
                continue
            if include_test_contents and is_test_object(taskfile.defined_in):
                continue
            tf_meta = TaskFileMetadata.from_taskfile(taskfile, findings.metadata)
            current = taskfiles.get(tf_meta.key, [])
            exists = False
            for tf_dict in current:
                tf = None
                if isinstance(tf_dict, dict):
                    tf = TaskFileMetadata.from_dict(tf_dict)
                elif isinstance(tf_dict, TaskFileMetadata):
                    tf = tf_dict
                if not tf:
                    continue
                if tf == tf_meta:
                    exists = True
                    break
            if not exists:
                current.append(tf_meta)
                new_data_found = True
            taskfiles.update({taskfile.key: current})
        if new_data_found:
            self.save_taskfile_index(taskfiles)
        return

    def register_action_group_index_to_ram(self, findings: Findings, include_test_contents: bool = False):
        new_data_found = False
        action_groups = self.load_action_group_index()

        for collection in findings.root_definitions.get("definitions", {}).get("collections", []):
            if not isinstance(collection, Collection):
                continue
            if collection.meta_runtime and isinstance(collection.meta_runtime, dict):
                for group_name, group_modules in collection.meta_runtime.get("action_groups", {}).items():
                    short_group_name = f"group/{group_name}"
                    fq_group_name = f"group/{collection.name}.{group_name}"

                    agm1 = ActionGroupMetadata.from_action_group(short_group_name, group_modules, findings.metadata)
                    current1 = action_groups.get(short_group_name, [])
                    exists = False
                    for ag_dict in current1:
                        ag = None
                        if isinstance(ag_dict, dict):
                            ag = ActionGroupMetadata.from_dict(ag_dict)
                        elif isinstance(ag_dict, ActionGroupMetadata):
                            ag = ag_dict
                        if not ag:
                            continue
                        if ag == agm1:
                            exists = True
                            break
                    if not exists:
                        current1.append(agm1)
                        new_data_found = True
                    action_groups.update({short_group_name: current1})

                    agm2 = ActionGroupMetadata.from_action_group(fq_group_name, group_modules, findings.metadata)
                    current2 = action_groups.get(fq_group_name, [])
                    exists = False
                    for ag_dict in current2:
                        ag = None
                        if isinstance(ag_dict, dict):
                            ag = ActionGroupMetadata.from_dict(ag_dict)
                        elif isinstance(ag_dict, ActionGroupMetadata):
                            ag = ag_dict
                        if not ag:
                            continue
                        if ag == agm2:
                            exists = True
                            break
                    if not exists:
                        current2.append(agm2)
                        new_data_found = True
                    action_groups.update({fq_group_name: current2})
        if new_data_found:
            self.save_action_group_index(action_groups)
        return

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
            # look for the module index with FQCN
            for possible_index in self.module_index[short_name]:
                if possible_index["fqcn"] == name:
                    found_index = possible_index
                    break
            # if any candidates don't match with FQCN, use the first index
            if not found_index:
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
            if findings_json in self.findings_cache:
                modules = self.findings_cache[findings_json].get("modules", [])
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                definitions = f.root_definitions.get("definitions", {})
                modules = definitions.get("modules", [])
                self.findings_cache[findings_json] = definitions
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

    def search_role(self, name, exact_match=False, max_match=-1, used_in=""):
        if max_match == 0:
            return []
        args_str = json.dumps([name, exact_match, max_match])
        if args_str in self.role_search_cache:
            return self.role_search_cache[args_str]

        from_indices = False
        found_index = None
        if name in self.role_index and self.role_index[name]:
            from_indices = True
            found_index = self.role_index[name][0]

        roles_json_list = []
        if from_indices:
            _type = found_index.get("type", "")
            _name = found_index.get("name", "")
            _version = found_index.get("version", "")
            _hash = found_index.get("hash", "")
            findings_path = os.path.join(self.root_dir, _type + "s", "findings", _name, _version, _hash, "findings.json")
            if os.path.exists(findings_path):
                roles_json_list.append(findings_path)
        else:
            # Do not search a role from all findings
            # when it is not found in the role index.
            # Instead, just return nothing in the case.
            pass

        matched_roles = []
        search_end = False
        for findings_json in roles_json_list:
            roles = ObjectList()
            if findings_json in self.findings_cache:
                roles = self.findings_cache[findings_json].get("roles", [])
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                definitions = f.root_definitions.get("definitions", {})
                roles = definitions.get("roles", [])
                self.findings_cache[findings_json] = definitions
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
                        _tmp_offspring_objects = self.search_taskfile(taskfile_key, is_key=True)
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
        self.role_search_cache[args_str] = matched_roles
        return matched_roles

    def make_taskfile_key_candidates(self, name, from_path, from_key):
        key_candidates = []
        taskfile_ref = name
        if from_path:
            base_path = os.path.dirname(from_path)
            taskfile_path = os.path.normpath(os.path.join(base_path, taskfile_ref))
            candidate_key_1 = make_imported_taskfile_key(from_key, taskfile_path)
            key_candidates.append(candidate_key_1)
            if "roles/" in taskfile_ref and "roles/" in base_path:
                root_path = base_path.split("roles/")[0]
                taskfile_path = os.path.normpath(os.path.join(root_path, taskfile_ref))
                candidate_key_2 = make_imported_taskfile_key(from_key, taskfile_path)
                key_candidates.append(candidate_key_2)

        return key_candidates

    def search_taskfile(self, name, from_path="", from_key="", max_match=-1, is_key=False, used_in=""):
        if max_match == 0:
            return []

        # it name is not an object key, we need `from_path` to create a key to be searched
        if not is_key and not from_path:
            return []

        args_str = json.dumps([name, from_path, from_key, max_match, is_key])
        if args_str in self.taskfile_search_cache:
            return self.taskfile_search_cache[args_str]

        from_indices = False
        found_index = None
        found_key = ""
        taskfile_key_candidates = []
        if is_key:
            taskfile_key_candidates = [name]
        else:
            taskfile_key_candidates = self.make_taskfile_key_candidates(name, from_path, from_key)
        for taskfile_key in taskfile_key_candidates:
            if taskfile_key in self.taskfile_index and self.taskfile_index[taskfile_key]:
                from_indices = True
                found_index = self.taskfile_index[taskfile_key][0]
                found_key = taskfile_key
                break

        taskfiles_json_list = []
        content_info = None
        if from_indices:
            _type = found_index.get("type", "")
            _name = found_index.get("name", "")
            _version = found_index.get("version", "")
            _hash = found_index.get("hash", "")
            content_info = found_index
            findings_path = os.path.join(self.root_dir, _type + "s", "findings", _name, _version, _hash, "findings.json")
            if os.path.exists(findings_path):
                taskfiles_json_list.append(findings_path)
        else:
            # Do not search a role from all findings
            # when it is not found in the role index.
            # Instead, just return nothing in the case.
            pass

        matched_taskfiles = []
        search_end = False
        for findings_json in taskfiles_json_list:
            taskfiles = ObjectList()
            if findings_json in self.findings_cache:
                taskfiles = self.findings_cache[findings_json].get("taskfiles", [])
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                definitions = f.root_definitions.get("definitions", {})
                taskfiles = definitions.get("taskfiles", [])
                self.findings_cache[findings_json] = definitions
            for tf in taskfiles:
                matched = False
                if tf.key == found_key:
                    matched = True

                # TODO: support taskfile reference with variables
                if matched:
                    parts = findings_json.split("/")
                    offspring_objects = []
                    for task_key in tf.tasks:
                        _tmp_offspring_objects = self.search_task(task_key, is_key=True, content_info=content_info, used_in=used_in)
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

    def search_task(self, name, exact_match=False, max_match=-1, is_key=False, content_info=None, used_in=""):
        if max_match == 0:
            return []
        # search task in RAM must be done for a specific content (collection/role)
        # so give up search here when no content_info is provided
        if not content_info or not isinstance(content_info, dict):
            return []

        args_str = json.dumps([name, exact_match, max_match, is_key, content_info])
        if args_str in self.task_search_cache:
            return self.task_search_cache[args_str]

        tasks_json_list = []
        _type = content_info.get("type", "")
        if _type:
            _type = _type + "s"
        _name = content_info.get("name", "")
        _version = content_info.get("version", "")
        _hash = content_info.get("hash", "")
        findings_path = os.path.join(self.root_dir, _type, "findings", _name, _version, _hash, "findings.json")
        if os.path.exists(findings_path):
            tasks_json_list.append(findings_path)

        matched_tasks = []
        search_end = False
        for findings_json in tasks_json_list:
            tasks = ObjectList()
            if findings_json in self.findings_cache:
                tasks = self.findings_cache[findings_json].get("tasks", [])
            else:
                f = Findings.load(fpath=findings_json)
                if not isinstance(f, Findings):
                    continue
                definitions = f.root_definitions.get("definitions", {})
                tasks = definitions.get("tasks", [])
                self.findings_cache[findings_json] = definitions
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
                        _tmp_offspring_objects = self.search_taskfile(t.executable, from_path=t.defined_in, from_key=t.key, used_in=t.defined_in)
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

    def search_action_group(self, name, max_match=-1):
        if max_match == 0:
            return []

        found_groups = []
        if name in self.action_group_index and self.action_group_index[name]:
            found_groups = self.action_group_index[name]

        if max_match > 0 and len(found_groups) > max_match:
            found_groups = found_groups[:max_match]
        return found_groups

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

    def init_findings_json_list_cache(self):
        search_patterns = os.path.join(self.root_dir, "collections", "findings", "*", "*", "*", "findings.json")
        findings_json_list_coll = safe_glob(search_patterns)
        findings_json_list_coll = sort_by_version(findings_json_list_coll)
        search_patterns = os.path.join(self.root_dir, "roles", "findings", "*", "*", "*", "findings.json")
        findings_json_list_role = safe_glob(search_patterns)
        findings_json_list_role = sort_by_version(findings_json_list_role)
        findings_json_list = findings_json_list_coll + findings_json_list_role
        self.findings_json_list_cache = findings_json_list

    def list_all_ram_metadata(self):
        if not self.findings_json_list_cache:
            self.init_findings_json_list_cache()
        findings_json_list = self.findings_json_list_cache

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
        if not self.findings_json_list_cache:
            self.init_findings_json_list_cache()
        args_str = json.dumps([target_name, target_version, target_type])
        if args_str in self.findings_search_cache:
            return self.findings_search_cache[args_str]

        if not target_name:
            raise ValueError("target name must be specified for searching RAM data")
        if not target_version:
            target_version = "*"
        findings_json_list = self.findings_json_list_cache
        found_path_list = []
        for findings_path in findings_json_list:
            parts = findings_path.split("/")
            _type = parts[-5][:-1]  # collection or role
            _name = parts[-4]
            _version = parts[-3]
            if _name != target_name:
                continue
            if target_version and target_version != "*":
                if _version != target_name:
                    continue
            if target_type and target_type != "*":
                if _type != target_type:
                    continue
            found_path_list.append(findings_path)

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

        self.findings_search_cache[args_str] = findings
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

    def save_index(self, index_objects, filename):
        out_dir = os.path.join(self.root_dir, "indices")
        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        index_objects_str = jsonpickle.encode(index_objects, make_refs=False, unpicklable=False)
        fpath = os.path.join(out_dir, filename)
        lock = lock_file(fpath)
        try:
            with open(fpath, "w") as file:
                file.write(index_objects_str)
        finally:
            unlock_file(lock)
            remove_lock_file(lock)

    def load_index(self, filename=""):
        path = os.path.join(self.root_dir, "indices", filename)
        index_objects = {}
        if os.path.exists(path):
            with open(path, "r") as file:
                index_objects = json.load(file)
        return index_objects

    def save_module_index(self, modules):
        return self.save_index(modules, module_index_name)

    def load_module_index(self):
        return self.load_index(module_index_name)

    def save_role_index(self, roles):
        return self.save_index(roles, role_index_name)

    def load_role_index(self):
        return self.load_index(role_index_name)

    def save_taskfile_index(self, taskfiles):
        return self.save_index(taskfiles, taskfile_index_name)

    def load_taskfile_index(self):
        return self.load_index(taskfile_index_name)

    def save_action_group_index(self, action_groups):
        return self.save_index(action_groups, action_group_index_name)

    def load_action_group_index(self):
        return self.load_index(action_group_index_name)

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
        with tarfile.open(outfile, "w:gz") as tar:
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
