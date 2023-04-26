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

from dataclasses import dataclass
from typing import List
from ansible_risk_insight.keyutil import detect_type
from ansible_risk_insight.models import (
    ObjectList,
    Repository,
    Playbook,
    Role,
    TaskCall,
    VariableAnnotation,
    Arguments,
    ArgumentsType,
    Variable,
    VariableType,
)
from ansible_risk_insight.context import Context, resolve_module_options
from ansible_risk_insight.annotators.annotator_base import Annotator, AnnotatorResult


class VariableAnnotator(Annotator):
    type: str = VariableAnnotation.type
    context: Context = None

    def __init__(self, context: Context):
        self.context = context

    def run(self, taskcall: TaskCall):
        resolved = resolve_module_options(self.context, taskcall)
        resolved_module_options = resolved[0]
        resolved_variables = resolved[1]
        # mutable_vars_per_mo = resolved[2]
        used_variables = resolved[3]
        _vars = []
        is_mutable = False
        for rv in resolved_variables:
            v_name = rv.get("key", "")
            v_value = rv.get("value", "")
            v_type = rv.get("type", VariableType.Unknown)
            elements = []
            if v_name in used_variables:
                if not isinstance(used_variables[v_name], dict):
                    continue
                for u_v_name, info in used_variables[v_name].items():
                    if u_v_name == v_name:
                        continue
                    u_v_value = info.get("value", "")
                    u_v_type = info.get("type", VariableType.Unknown)
                    u_v = Variable(
                        name=u_v_name,
                        value=u_v_value,
                        type=u_v_type,
                        used_in=taskcall.key,
                    )
                    elements.append(u_v)
            v = Variable(
                name=v_name,
                value=v_value,
                type=v_type,
                elements=elements,
                used_in=taskcall.key,
            )
            _vars.append(v)
            if v.is_mutable:
                is_mutable = True

        for v in _vars:
            history = self.context.var_use_history.get(v.name, [])
            history.append(v)
            self.context.var_use_history[v.name] = history

        m_opts = taskcall.spec.module_options
        if isinstance(m_opts, list):
            args_type = ArgumentsType.LIST
        elif isinstance(m_opts, dict):
            args_type = ArgumentsType.DICT
        else:
            args_type = ArgumentsType.SIMPLE
        args = Arguments(
            type=args_type,
            raw=m_opts,
            vars=_vars,
            resolved=True,  # TODO: False if not resolved
            templated=resolved_module_options,
            is_mutable=is_mutable,
        )
        taskcall.args = args
        # deep copy the history here because the context is updated by subsequent taskcalls
        if self.context.var_set_history:
            taskcall.variable_set = self.context.var_set_history.copy()
        if self.context.var_use_history:
            taskcall.variable_use = self.context.var_use_history.copy()
        taskcall.become = self.context.become
        taskcall.module_defaults = self.context.module_defaults

        return VariableAnnotatorResult()


@dataclass
class VariableAnnotatorResult(AnnotatorResult):
    pass


def tree_to_task_list(tree, node_objects):
    node_dict = {}
    for no in node_objects.items:
        node_dict[no.key] = no

    def getSubTree(node):
        tasks = []
        resolved_name = ""
        no = node_dict[node.key]
        node_type = detect_type(node.key)

        children_tasks = []
        if node_type == "module":
            resolved_name = no.fqcn
        elif node_type == "role":
            resolved_name = no.fqcn
        elif node_type == "taskfile":
            resolved_name = no.key

        children_per_type = {}
        for c in node.children:
            ctype = detect_type(c.key)
            if ctype in children_per_type:
                children_per_type[ctype].append(c)
            else:
                children_per_type[ctype] = [c]

        # obj["children_types"] = list(children_per_type.keys())
        if "playbook" in children_per_type:
            tasks_per_children = [getSubTree(c) for c in children_per_type["playbook"]]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
        if "play" in children_per_type:
            tasks_per_children = [getSubTree(c) for c in children_per_type["play"]]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
        if "role" in children_per_type:
            tasks_per_children = [getSubTree(c) for c in children_per_type["role"]]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
            if node_type == "task":
                fqcns = [fqcn for (_, fqcn) in tasks_per_children]
                resolved_name = fqcns[0] if len(fqcns) > 0 else ""
        if "taskfile" in children_per_type:
            tasks_per_children = [getSubTree(c) for c in children_per_type["taskfile"]]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
            if node_type == "task":
                _tf_path_list = [_tf_path for (_, _tf_path) in tasks_per_children]
                resolved_name = _tf_path_list[0] if len(_tf_path_list) > 0 else ""
        if "task" in children_per_type:
            tasks_per_children = [getSubTree(c) for c in children_per_type["task"]]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
        if "module" in children_per_type:
            if node_type == "task":
                fqcns = [getSubTree(c)[1] for c in children_per_type["module"]]
                resolved_name = fqcns[0] if len(fqcns) > 0 else ""

        if node_type == "task":
            no.resolved_name = resolved_name
            tasks.append(no.__dict__)
        tasks.extend(children_tasks)
        return tasks, resolved_name

    tasks, _ = getSubTree(tree)
    return tasks


def resolve_variables(tree: ObjectList, additional: ObjectList) -> List[TaskCall]:
    tree_root_key = tree.items[0].spec.key if len(tree.items) > 0 else ""
    inventories = get_inventories(tree_root_key, additional)
    context = Context(inventories=inventories)
    depth_dict = {}
    resolved_taskcalls = []
    for call_obj in tree.items:
        caller_depth_lvl = 0
        if call_obj.called_from != "":
            caller_key = call_obj.called_from
            caller_depth_lvl = depth_dict.get(caller_key, 0)
        depth_lvl = caller_depth_lvl + 1
        depth_dict[call_obj.key] = depth_lvl
        context.add(call_obj, depth_lvl)
        if isinstance(call_obj, TaskCall):
            result = VariableAnnotator(context=context).run(call_obj)
            if not result:
                continue
            if result.annotations:
                call_obj.annotations.extend(result.annotations)
            resolved_taskcalls.append(call_obj)
    return resolved_taskcalls


def get_inventories(tree_root_key, additional):
    if tree_root_key == "":
        return []
    tree_root_type = detect_type(tree_root_key)
    projects = additional.find_by_type("repository")
    inventories = []
    found = False
    for p in projects:
        if not isinstance(p, Repository):
            continue
        if tree_root_type == "playbook":
            for playbook in p.playbooks:
                if isinstance(playbook, str):
                    if playbook == tree_root_key:
                        inventories = p.inventories
                        found = True
                elif isinstance(playbook, Playbook):
                    if playbook.key == tree_root_key:
                        inventories = p.inventories
                        found = True
                if found:
                    break
        elif tree_root_type == "role":
            for role in p.roles:
                if isinstance(role, str):
                    if role == tree_root_key:
                        inventories = p.inventories
                        found = True
                elif isinstance(role, Role):
                    if role.key == tree_root_key:
                        inventories = p.inventories
                        found = True
                if found:
                    break
        if found:
            break
    return inventories
