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

import logging
import os
import re
import json
from copy import deepcopy
from dataclasses import dataclass, field
from .keyutil import detect_type, key_delimiter, object_delimiter
from .models import (
    ObjectList,
    Playbook,
    Play,
    RoleInPlay,
    Role,
    Task,
    TaskFile,
    ExecutableType,
    Module,
    LoadType,
    CallObject,
    TaskCall,
    call_obj_from_spec,
)
from .finder import get_builtin_module_names

obj_type_dict = {
    "playbook": "playbooks",
    "play": "plays",
    "role": "roles",
    "taskfile": "taskfiles",
    "task": "tasks",
    "module": "modules",
}

module_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")
role_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
role_in_collection_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")


@dataclass
class TreeNode(object):
    key: str = ""

    # children is a list of TreeNode
    children: list = field(default_factory=list)

    definition: dict = field(default_factory=dict)

    # load a list of (src, dst) as a tree structure
    # which is composed of multiple TreeNode
    @staticmethod
    def load(graph=[]):
        root_key_cands = [pair[1] for pair in graph if pair[0] is None]
        if len(root_key_cands) != 1:
            raise ValueError("tree array must have only one top with src == None, but" " found {}".format(len(root_key_cands)))
        root_key = root_key_cands[0]
        tree = TreeNode()
        tree, _ = tree.recursive_tree_load(root_key, graph)
        tree.key = root_key
        tree.children = tree.children
        tree.definition = tree.definition
        return tree

    # output list of (src, dst) to stdout or file
    def dump(self, path=""):
        src_dst_array = self.to_graph()
        if path == "":
            print(json.dumps(src_dst_array, indent=2))
        else:
            tree_json = json.dumps(src_dst_array)
            with open(path, "w") as file:
                file.write(tree_json)

    def to_str(self):
        src_dst_array = self.to_graph()
        return json.dumps(src_dst_array)

    # return list of (src, dst)
    def to_graph(self):
        return self.recursive_graph_dump(None, self)

    # return list of dst keys
    def to_keys(self):
        return [p[1] for p in self.to_graph()]

    # reutrn list of TreeNodes that are under this TreeNode
    def to_list(self):
        return self.recursive_convert_to_list(self)

    def recursive_convert_to_list(self, node, nodelist=[]):
        current = [pair for pair in nodelist]
        current.append(node)
        for child_node in node.children:
            current = self.recursive_convert_to_list(child_node, current)
        return current

    def recursive_tree_load(self, node_key, src_dst_array, parent_keys=None):
        if parent_keys is None:
            parent_keys = set()
        n = TreeNode(key=node_key)
        if node_key in parent_keys:
            return n, parent_keys
        parent_keys.add(node_key)
        new_parent_keys = parent_keys.copy()
        for (src_key, dst_key) in src_dst_array:
            children_keys = []
            if node_key == src_key:
                children_keys.append(dst_key)
            for c_key in children_keys:
                child_tree, sub_parent_keys = self.recursive_tree_load(c_key, src_dst_array, parent_keys)
                n.children.append(child_tree)
                new_parent_keys = new_parent_keys.union(sub_parent_keys)
        return n, new_parent_keys

    def recursive_graph_dump(self, parent_node, node, src_dst_array=[]):
        current = [pair for pair in src_dst_array]
        src = None if parent_node is None else parent_node.key
        dst = node.key
        current.append((src, dst))
        for child_node in node.children:
            is_included = len([(src, dst) for (src, dst) in current if src == child_node.key]) > 0
            if is_included:
                continue
            current = self.recursive_graph_dump(node, child_node, current)
        return current

    # return a list of (src, dst) which ends with the "end_key"
    # this could return multiple paths
    def path_to_root(self, end_key):
        path_array = self.search_branch_to_key(end_key, self)
        path_array = [nodelist2branch(nodelist) for nodelist in path_array]
        return path_array

    def search_branch_to_key(self, search_key, node, ancestors=[]):
        current = [n for n in ancestors]
        found = []
        if node.key == search_key:
            found = current + [node]
        for child_node in node.children:
            found_in_child = self.search_branch_to_key(search_key, child_node, current + [node])
            found.extend(found_in_child)
        return found

    def copy(self):
        return deepcopy(self)

    @property
    def is_empty(self):
        return self.key == "" and len(self.children) == 0

    @property
    def has_definition(self):
        return len(self.definition) == 0


def nodelist2branch(nodelist):
    if len(nodelist) == 0:
        return TreeNode()
    t = nodelist[0].copy()
    current = t
    for i, n in enumerate(nodelist):
        if i == 0:
            continue
        current.children = [n.copy()]
        current = current.children[0]
    return t


def load_single_definition(defs: dict, key: str):
    obj_list = ObjectList()
    items = defs.get(key, [])
    for item in items:
        obj_list.add(item)
    return obj_list


def load_definitions(defs: dict, types: list):
    def_list = []
    for type_key in types:
        objs_per_type = load_single_definition(defs, type_key)
        def_list.append(objs_per_type)
    return def_list


def load_all_definitions(definitions: dict):
    _definitions = {}
    if "mappings" in definitions:
        _definitions = {"root": definitions}
    else:
        _definitions = definitions
    loaded = {}
    types = ["roles", "taskfiles", "modules", "playbooks", "plays", "tasks"]
    for type_key in types:
        loaded[type_key] = ObjectList()
    for _, definitions_per_artifact in _definitions.items():
        def_list = load_definitions(definitions_per_artifact.get("definitions", {}), types)
        for i, type_key in enumerate(types):
            if type_key not in loaded:
                loaded[type_key] = def_list[i]
            else:
                loaded[type_key].merge(def_list[i])
    return loaded


def make_dicts(root_definitions, ext_definitions):
    definitions = {
        "roles": ObjectList(),
        "modules": ObjectList(),
        "taskfiles": ObjectList(),
        "playbooks": ObjectList(),
    }
    for type_key in definitions:
        definitions[type_key].merge(root_definitions.get(type_key, ObjectList()))
        definitions[type_key].merge(ext_definitions.get(type_key, ObjectList()))
    dicts = {}
    for type_key, obj_list in definitions.items():
        for obj in obj_list.items:
            obj_dict_key = obj.fqcn if hasattr(obj, "fqcn") else obj.key
            if type_key not in dicts:
                dicts[type_key] = {}
            dicts[type_key][obj_dict_key] = obj
    return dicts


def resolve(obj, dicts):
    failed = False
    if isinstance(obj, Task):
        task = obj
        if task.executable != "":
            if task.executable_type == ExecutableType.MODULE_TYPE:
                task.resolved_name = resolve_module(task.executable, dicts.get("modules", {}))
            elif task.executable_type == ExecutableType.ROLE_TYPE:
                task.resolved_name = resolve_role(
                    task.executable,
                    dicts.get("roles", {}),
                    task.collection,
                    task.collections_in_play,
                )
            elif task.executable_type == ExecutableType.TASKFILE_TYPE:
                task.resolved_name = resolve_taskfile(task.executable, dicts.get("taskfiles", {}), task.key)
            if task.resolved_name == "":
                failed = True
    elif isinstance(obj, Play):
        for i in range(len(obj.roles)):
            roleinplay = obj.roles[i]
            if not isinstance(roleinplay, RoleInPlay):
                continue
            roleinplay.resolved_name = resolve_role(
                roleinplay.name,
                dicts.get("roles", {}),
                roleinplay.collection,
                roleinplay.collections_in_play,
            )
            obj.roles[i] = roleinplay
            if roleinplay.resolved_name == "":
                failed = True
    return obj, failed


def resolve_module(module_name, module_dict={}):
    module_key = ""
    found_module = module_dict.get(module_name, None)
    if found_module is not None:
        module_key = found_module.key
    if module_key == "":
        for k in module_dict:
            suffix = ".{}".format(module_name)
            if k.endswith(suffix):
                module_key = module_dict[k].key
                break
    return module_key


def resolve_role(role_name, role_dict={}, my_collection_name="", collections_in_play=[]):
    role_key = ""
    if "." not in role_name and len(collections_in_play) > 0:
        for coll in collections_in_play:
            role_name_cand = "{}.{}".format(coll, role_name)
            found_role = role_dict.get(role_name_cand, None)
            if found_role is not None:
                role_key = found_role.key
    else:
        if "." not in role_name and my_collection_name != "":
            role_name_cand = "{}.{}".format(my_collection_name, role_name)
            found_role = role_dict.get(role_name_cand, None)
            if found_role is not None:
                role_key = found_role.key
        if role_key == "":
            found_role = role_dict.get(role_name, None)
            if found_role is not None:
                role_key = found_role.key
            else:
                for k in role_dict:
                    suffix = ".{}".format(role_name)
                    if k.endswith(suffix):
                        role_key = role_dict[k].key
                        break
    return role_key


def resolve_taskfile(taskfile_ref, taskfile_dict={}, task_key=""):
    type_prefix = "task "
    parts = task_key[len(type_prefix) :].split(object_delimiter)
    parent_key = ""
    task_defined_path = ""
    for p in parts[::-1]:
        if p.startswith("playbook" + key_delimiter) or p.startswith("taskfile" + key_delimiter):
            task_defined_path = p.split(key_delimiter)[1]
            parent_key = task_key[len(type_prefix) :].split(p)[0]
            break

    # include/import tasks can have a path like "roles/xxxx/tasks/yyyy.yml"
    # then try to find roles directory
    if taskfile_ref.startswith("roles/"):
        if "roles/" in task_defined_path:
            roles_parent_dir = task_defined_path.split("roles/")[0]
            fpath = os.path.join(roles_parent_dir, taskfile_ref)
            fpath = os.path.normpath(fpath)
            taskfile_key = "taskfile {}taskfile{}{}".format(parent_key, key_delimiter, fpath)
            found_tf = taskfile_dict.get(taskfile_key, None)
            if found_tf is not None:
                return found_tf.key

    task_dir = os.path.dirname(task_defined_path)
    fpath = os.path.join(task_dir, taskfile_ref)
    # need to normalize path here because taskfile_ref can be
    # something like "../some_taskfile.yml".
    # it should be "tasks/some_taskfile.yml"
    fpath = os.path.normpath(fpath)
    taskfile_key = "taskfile {}taskfile{}{}".format(parent_key, key_delimiter, fpath)
    found_tf = taskfile_dict.get(taskfile_key, None)
    if found_tf is not None:
        return found_tf.key

    return ""


def resolve_playbook(playbook_ref, playbook_dict={}, play_key=""):
    type_prefix = "play "
    parts = play_key[len(type_prefix) :].split(object_delimiter)
    parent_key = ""
    play_defined_path = ""
    for p in parts[::-1]:
        if p.startswith("playbook" + key_delimiter):
            play_defined_path = p.split(key_delimiter)[1]
            parent_key = play_key[len(type_prefix) :].split(p)[0]
            break

    play_dir = os.path.dirname(play_defined_path)
    fpath = os.path.join(play_dir, playbook_ref)
    # need to normalize path here because playbook_ref can be
    # something like "../some_playbook.yml"
    fpath = os.path.normpath(fpath)
    playbook_key = "playbook {}playbook{}{}".format(parent_key, key_delimiter, fpath)
    found_playbook = playbook_dict.get(playbook_key, None)
    if found_playbook is not None:
        return found_playbook.key
    return ""


def init_builtin_modules():
    builtin_module_names = get_builtin_module_names()
    modules = []
    for module_name in builtin_module_names:
        collection_name = "ansible.builtin"
        fqcn = "{}.{}".format(collection_name, module_name)
        global_key = "module collection{}{}{}module{}{}".format(
            key_delimiter,
            collection_name,
            object_delimiter,
            key_delimiter,
            fqcn,
        )
        local_key = "module module{}{}".format(key_delimiter, "__builtin__")
        m = Module(
            name=module_name,
            fqcn=fqcn,
            key=global_key,
            local_key=local_key,
            collection=collection_name,
            builtin=True,
        )
        modules.append(m)
    return modules


class TreeLoader(object):
    def __init__(self, root_definitions, ext_definitions):

        # use mappings just to get tree tops (playbook/role)
        # we don't load any files by this mappings here
        self.load_and_mapping = root_definitions.get("mappings", None)
        self.playbook_mappings = self.load_and_mapping.playbooks
        self.role_mappings = self.load_and_mapping.roles

        # TODO: dependency check, especially for
        # collection dependencies for role

        self.org_root_definitions = root_definitions
        self.org_ext_definitions = ext_definitions

        self.root_definitions = load_all_definitions(root_definitions)
        self.ext_definitions = load_all_definitions(ext_definitions)
        self.add_builtin_modules()

        self.dicts = make_dicts(self.root_definitions, self.ext_definitions)

        self.trees = []
        return

    def run(self):
        additional_objects = ObjectList()
        if self.load_and_mapping.target_type == LoadType.PROJECT:
            p_defs = self.org_root_definitions.get("definitions", {}).get("projects", [])
            if len(p_defs) > 0:
                additional_objects.add(p_defs[0])
            logging.info("  project loaded")
        logging.info("  start building playbook trees")
        for i, mapping in enumerate(self.playbook_mappings):
            logging.debug("[{}/{}] {}".format(i + 1, len(self.playbook_mappings), mapping[1]))
            playbook_key = mapping[1]
            tree_objects = self._recursive_get_calls(playbook_key)
            self.trees.append(tree_objects)
        logging.info("  done")
        logging.info("  start building role trees")
        for i, mapping in enumerate(self.role_mappings):
            logging.debug("[{}/{}] {}".format(i + 1, len(self.role_mappings), mapping[1]))
            role_key = mapping[1]
            tree_objects = self._recursive_get_calls(role_key)
            self.trees.append(tree_objects)
        logging.info("  done")
        return self.trees, additional_objects

    def _recursive_get_calls(self, key, caller=None):
        obj_list = ObjectList()
        obj = self.get_object(key)
        if obj is None:
            return obj_list
        call_obj = call_obj_from_spec(spec=obj, caller=caller)
        if call_obj is not None:
            obj_list.add(call_obj, update_dict=False)
        children_keys = self._get_children_keys(obj)
        for c_key in children_keys:
            child_objects = self._recursive_get_calls(
                c_key,
                call_obj,
            )
            if isinstance(call_obj, TaskCall):
                taskcall = call_obj
                if len(child_objects.items) > 0:
                    c_obj = child_objects.items[0]
                    if taskcall.spec.executable_type == ExecutableType.MODULE_TYPE:
                        taskcall.spec.resolved_name = c_obj.spec.fqcn
                    elif taskcall.spec.executable_type == ExecutableType.ROLE_TYPE:
                        taskcall.spec.resolved_name = c_obj.spec.fqcn
                    elif taskcall.spec.executable_type == ExecutableType.TASKFILE_TYPE:
                        taskcall.spec.resolved_name = c_obj.spec.key
            obj_list.merge(child_objects)
        return obj_list

    def _recursive_make_graph(self, key, graph, _objects, caller=None):
        current_graph = [g for g in graph]
        # if this key is already in the graph src, no need to trace children
        key_in_graph_src = [g for g in current_graph if g[0] == key]
        if len(key_in_graph_src) > 0:
            return current_graph
        # otherwise, trace children
        obj = self.get_object(key)
        if obj is None:
            return current_graph
        call_obj = call_obj_from_spec(spec=obj, caller=caller)
        if call_obj is not None:
            caller_key = None if caller is None else caller.key
            my_key = call_obj.key
            current_graph.append([caller_key, my_key])
            _objects.add(call_obj, update_dict=False)
        children_keys = self._get_children_keys(obj)
        for c_key in children_keys:
            updated_graph = self._recursive_make_graph(
                c_key,
                current_graph,
                _objects,
                call_obj,
            )
            current_graph = updated_graph
        return current_graph

    # get definition object from root/ext definitions
    def get_object(self, obj_key):
        obj_type = detect_type(obj_key)
        if obj_type == "":
            raise ValueError('failed to detect object type from key "{}"'.format(obj_key))
        type_key = obj_type_dict[obj_type]
        root_definitions = self.root_definitions.get(type_key, ObjectList())
        obj = root_definitions.find_by_key(obj_key)
        if obj is not None:
            return obj
        ext_definitions = self.ext_definitions.get(type_key, ObjectList())
        obj = ext_definitions.find_by_key(obj_key)
        if obj is not None:
            return obj
        return None

    def add_builtin_modules(self):
        obj_list = ObjectList()
        builtin_modules = init_builtin_modules()
        for m in builtin_modules:
            obj_list.add(m)
        self.ext_definitions["modules"].merge(obj_list)

    def _get_children_keys(self, obj):
        if isinstance(obj, CallObject):
            return self._get_children_keys(obj.spec)
        children_keys = []
        if isinstance(obj, Playbook):
            children_keys = obj.plays
        elif isinstance(obj, Play):
            if obj.import_playbook != "":
                resolved_playbook_key = resolve_playbook(obj.import_playbook, self.dicts["playbooks"], obj.key)
                if resolved_playbook_key != "":
                    children_keys.append(resolved_playbook_key)
            children_keys.extend(obj.pre_tasks)
            children_keys.extend(obj.tasks)
            for rip in obj.roles:
                resolved_role_key = resolve_role(
                    rip.name,
                    self.dicts["roles"],
                    obj.collection,
                    obj.collections_in_play,
                )
                if resolved_role_key != "":
                    children_keys.append(resolved_role_key)
            children_keys.extend(obj.post_tasks)
        elif isinstance(obj, Role):
            main_taskfile_key = [tf for tf in obj.taskfiles if tf.split(key_delimiter)[-1].split("/")[-1] in ["main.yml", "main.yaml"]]
            children_keys.extend(main_taskfile_key)
        elif isinstance(obj, TaskFile):
            children_keys = obj.tasks
        elif isinstance(obj, Task):
            executable_type = obj.executable_type
            resolved_key = ""
            if executable_type == ExecutableType.MODULE_TYPE:
                resolved_key = resolve_module(obj.executable, self.dicts["modules"])
            elif executable_type == ExecutableType.ROLE_TYPE:
                resolved_key = resolve_role(
                    obj.executable,
                    self.dicts["roles"],
                    obj.collection,
                    obj.collections_in_play,
                )
            elif executable_type == ExecutableType.TASKFILE_TYPE:
                resolved_key = resolve_taskfile(obj.executable, self.dicts["taskfiles"], obj.key)
            if resolved_key != "":
                children_keys.append(resolved_key)
        return children_keys

    def node_objects(self, tree):
        loaded = {}
        obj_list = ObjectList()
        for k in tree.to_keys():
            if k in loaded:
                obj_list.add(loaded[k])
                continue
            obj = self.get_object(k)
            if obj is None:
                logging.warning("object not found for the key {}".format(k))
                continue
            obj_list.add(obj)
            loaded[k] = obj
        return obj_list


def dump_node_objects(obj_list, path=""):
    if path == "":
        lines = obj_list.dump()
        for line in lines:
            obj_dict = json.loads(line)
            print(json.dumps(obj_dict, indent=2))
    else:
        obj_list.dump(fpath=path)


def key_to_file_name(prefix, key):
    return prefix + "___" + key.translate(str.maketrans({" ": "___", "/": "---", ".": "_dot_"})) + ".json"
