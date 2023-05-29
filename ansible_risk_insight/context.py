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
import re
import copy
from dataclasses import dataclass, field
from pathlib import Path
from .models import (
    Playbook,
    Play,
    Role,
    Collection,
    TaskFile,
    Task,
    TaskCall,
    InventoryType,
    Object,
    CallObject,
    Variable,
    VariableType,
    BecomeInfo,
    immutable_var_types,
)

p = Path(__file__).resolve().parent
ansible_special_variables = [line.replace("\n", "") for line in open(p / "ansible_variables.txt", "r").read().splitlines()]
_special_var_value = "__ansible_special_variable__"
variable_block_re = re.compile(r"{{[^}]+}}")


def get_object(json_path, type, name, cache={}):
    json_type = ""
    json_str = ""
    cached = cache.get(json_path, None)
    if cached is None:
        if not os.path.exists(json_path):
            raise ValueError('the json path "{}" not found'.format(json_path))
        basename = os.path.basename(json_path)

        if basename.startswith("role-"):
            json_type = "role"
            with open(json_path, "r") as file:
                json_str = file.read()
        elif basename.startswith("collection-"):
            json_type = "collection"
            with open(json_path, "r") as file:
                json_str = file.read()
        if json_str == "":
            raise ValueError("json data is empty")
        cache.update({json_path: (json_type, json_str)})
    else:
        json_type, json_str = cached[0], cached[1]
    if json_type == "role":
        r = Role.from_json(json_str)
        if type == "collection":
            raise ValueError("collection cannot be gotten in a role")
        if type == "role":
            return r
        elif type == "playbook":
            raise ValueError("playbook cannot be gotten in a role")
        elif type == "taskfile":
            for tf in r.taskfiles:
                if tf.defined_in == name:
                    return tf
        elif type == "task":
            for tf in r.taskfiles:
                for t in tf.tasks:
                    if t.id == name:
                        return t
        elif type == "module":
            for m in r.modules:
                if m.fqcn == name:
                    return m
        return None
    elif json_type == "collection":
        c = Collection()
        c.from_json(json_str)
        if type == "collection":
            return c
        if type == "role":
            for r in c.roles:
                if r.fqcn == name:
                    return r
        elif type == "playbook":
            for p in c.playbooks:
                if p.defined_in == name:
                    return p
        elif type == "taskfile":
            for tf in c.taskfiles:
                if tf.defined_in == name:
                    return tf
            for r in c.roles:
                for tf in r.taskfiles:
                    if tf.defined_in == name:
                        return tf
        elif type == "task":
            for p in c.playbooks:
                for t in p.tasks:
                    if t.id == name:
                        return t
            for tf in c.taskfiles:
                for t in tf.tasks:
                    if t.id == name:
                        return t
            for r in c.roles:
                for tf in r.taskfiles:
                    for t in tf.tasks:
                        if t.id == name:
                            return t
        elif type == "module":
            for m in c.modules:
                if m.fqcn == name:
                    return m
        return None
    return None


def recursive_find_variable(var_name, var_dict={}):
    def _visitor(vname, nname, node):
        if nname == vname:
            return node
        if isinstance(node, dict):
            if nname in node:
                return node[nname]
            for k, v in node.items():
                nname2 = "{}.{}".format(nname, k) if nname != "" else k
                if vname.startswith("{}.".format(nname2)):
                    vname2 = vname[len(nname) + 1 :]
                    return _visitor(vname2, nname2, v)
            return None
        else:
            return None

    return _visitor(var_name, "", var_dict)


def flatten(var_dict: dict = {}, _prefix: str = ""):
    flat_vars = {}
    for k, v in var_dict.items():
        if isinstance(v, dict):
            new_prefix = f"{k}." if _prefix == "" else f"{_prefix}{k}"
            sub_flat_vars = flatten(v, new_prefix)
            flat_vars.update(sub_flat_vars)
        else:
            flat_key = f"{_prefix}{k}"
            flat_vars.update({flat_key: v})
    return flat_vars


@dataclass
class Context:
    keep_obj: bool = False
    chain: list = field(default_factory=list)
    variables: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    inventories: list = field(default_factory=list)
    role_defaults: list = field(default_factory=list)
    role_vars: list = field(default_factory=list)
    registered_vars: list = field(default_factory=list)
    set_facts: list = field(default_factory=list)
    task_vars: list = field(default_factory=list)

    become: BecomeInfo = None
    module_defaults: dict = field(default_factory=dict)

    var_set_history: dict = field(default_factory=dict)
    var_use_history: dict = field(default_factory=dict)

    _flat_vars: dict = field(default_factory=dict)

    def add(self, obj, depth_lvl=0):
        _obj = None
        _spec = None
        if isinstance(obj, Object):
            _obj = obj
            _spec = obj
        elif isinstance(obj, CallObject):
            _obj = obj
            _spec = obj.spec
        # variables
        if isinstance(_spec, Playbook):
            self.variables.update(_spec.variables)
            self.update_flat_vars(_spec.variables)
            for key, val in _spec.variables.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.PlaybookGroupVarsAll, setter=_spec.key))
                self.var_set_history[key] = current
        elif isinstance(_spec, Play):
            self.variables.update(_spec.variables)
            self.update_flat_vars(_spec.variables)
            for key, val in _spec.variables.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.PlayVars, setter=_spec.key))
                self.var_set_history[key] = current
            if _spec.become:
                self.become = _spec.become
            if _spec.module_defaults:
                self.module_defaults = _spec.module_defaults
        elif isinstance(_spec, Role):
            self.variables.update(_spec.default_variables)
            self.update_flat_vars(_spec.default_variables)
            self.variables.update(_spec.variables)
            self.update_flat_vars(_spec.variables)
            for var_name in _spec.default_variables:
                self.role_defaults.append(var_name)
            for var_name in _spec.variables:
                self.role_vars.append(var_name)
            for key, val in _spec.default_variables.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.RoleDefaults, setter=_spec.key))
                self.var_set_history[key] = current
            for key, val in _spec.variables.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.RoleVars, setter=_spec.key))
                self.var_set_history[key] = current
        elif isinstance(_spec, Collection):
            self.variables.update(_spec.variables)
            self.update_flat_vars(_spec.variables)
        elif isinstance(_spec, TaskFile):
            self.variables.update(_spec.variables)
            self.update_flat_vars(_spec.variables)
        elif isinstance(_spec, Task):
            self.variables.update(_spec.variables)
            self.update_flat_vars(_spec.variables)
            self.variables.update(_spec.registered_variables)
            self.update_flat_vars(_spec.registered_variables)
            self.variables.update(_spec.set_facts)
            self.update_flat_vars(_spec.set_facts)
            for var_name in _spec.registered_variables:
                self.registered_vars.append(var_name)
            for var_name in _spec.set_facts:
                self.set_facts.append(var_name)
            for key, val in _spec.variables.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.TaskVars, setter=_spec.key))
                self.var_set_history[key] = current
            for key, val in _spec.registered_variables.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.RegisteredVars, setter=_spec.key))
                self.var_set_history[key] = current
            for key, val in _spec.set_facts.items():
                current = self.var_set_history.get(key, [])
                current.append(Variable(name=key, value=val, type=VariableType.SetFacts, setter=_spec.key))
                self.var_set_history[key] = current
            if _spec.become:
                self.become = _spec.become
            if _spec.module_defaults:
                self.module_defaults = _spec.module_defaults
        else:
            # Module
            return
        self.options.update(_spec.options)
        chain_node = {"key": _obj.key, "depth": depth_lvl}
        if self.keep_obj:
            chain_node["obj"] = _obj
        self.chain.append(chain_node)

    def resolve_variable(self, var_name, resolve_history={}):
        if var_name in resolve_history:
            val = resolve_history[var_name].get("value", None)
            v_type = resolve_history[var_name].get("type", VariableType.Unknown)
            return val, v_type, resolve_history

        _resolve_history = resolve_history.copy()

        v_type = None
        if var_name in ansible_special_variables:
            v_type = VariableType.HostFacts
            return None, v_type, resolve_history

        if var_name in self.role_vars:
            v_type = VariableType.RoleVars
        elif var_name in self.role_defaults:
            v_type = VariableType.RoleDefaults
        elif var_name in self.registered_vars:
            v_type = VariableType.RegisteredVars
        elif var_name in self.set_facts:
            v_type = VariableType.SetFacts
        else:
            v_type = VariableType.TaskVars

        val = self.variables.get(var_name, None)
        if val is not None:
            _resolve_history[var_name] = {"value": val, "type": v_type}

            if isinstance(val, str):
                resolved_val, _resolve_history = self.resolve_single_variable(val, _resolve_history)
                return resolved_val, v_type, _resolve_history
            elif isinstance(val, list):
                resolved_val_list = []
                for vi in val:
                    resolved_val, _resolve_history = self.resolve_single_variable(vi, _resolve_history)
                    resolved_val_list.append(resolved_val)
                return resolved_val_list, v_type, _resolve_history
            else:
                return val, v_type, _resolve_history

        val = self._flat_vars.get(var_name, None)
        if val is not None:
            _resolve_history[var_name] = {"value": val, "type": v_type}

            if isinstance(val, str):
                resolved_val, _resolve_history = self.resolve_single_variable(val, _resolve_history)
                return resolved_val, v_type, _resolve_history
            elif isinstance(val, list):
                resolved_val_list = []
                for vi in val:
                    resolved_val, _resolve_history = self.resolve_single_variable(vi, _resolve_history)
                    resolved_val_list.append(resolved_val)
                return resolved_val_list, v_type, _resolve_history
            else:
                return val, v_type, _resolve_history

        # TODO: consider group
        inventory_for_all = [iv for iv in self.inventories if iv.inventory_type == InventoryType.GROUP_VARS_TYPE and iv.name == "all"]
        for iv in inventory_for_all:
            iv_var_dict = flatten(iv.variables)
            val = iv_var_dict.get(var_name, None)

            if val is not None:
                _resolve_history[var_name] = {"value": val, "type": v_type}
                v_type = VariableType.InventoryGroupVarsAll
                if isinstance(val, str):
                    resolved_val, _resolve_history = self.resolve_single_variable(val, _resolve_history)
                    return resolved_val, v_type, _resolve_history
                elif isinstance(val, list):
                    resolved_val_list = []
                    for vi in val:
                        resolved_val, _resolve_history = self.resolve_single_variable(vi, _resolve_history)
                        resolved_val_list.append(resolved_val)
                    return resolved_val_list, v_type, _resolve_history
                else:
                    return val, v_type, _resolve_history

        _resolve_history[var_name] = {"value": None, "type": VariableType.Unknown}

        return None, VariableType.Unknown, _resolve_history

    def resolve_single_variable(self, txt, resolve_history=[]):
        new_history = resolve_history.copy()
        if not isinstance(txt, str):
            return txt, new_history
        if "{{" in txt:
            var_names_in_txt = extract_variable_names(txt)
            if len(var_names_in_txt) == 0:
                return txt, new_history
            resolved_txt = txt
            for var_name_in_txt in var_names_in_txt:
                original_block = var_name_in_txt.get("original", "")
                var_name = var_name_in_txt.get("name", "")
                default_var_name = var_name_in_txt.get("default", "")
                var_val_in_txt, _, new_history = self.resolve_variable(var_name, new_history)
                if var_val_in_txt is None and default_var_name != "":
                    var_val_in_txt, _, new_history = self.resolve_variable(default_var_name, new_history)
                if var_val_in_txt is None:
                    return resolved_txt, new_history
                if txt == original_block:
                    return var_val_in_txt, new_history
                resolved_txt = resolved_txt.replace(original_block, str(var_val_in_txt))
            return resolved_txt, new_history
        else:
            return txt, new_history

    def update_flat_vars(self, new_vars: dict, _prefix: str = ""):
        for k, v in new_vars.items():
            if isinstance(v, dict):
                new_prefix = f"{k}." if _prefix == "" else f"{_prefix}{k}"
                self.update_flat_vars(v, new_prefix)
            else:
                flat_key = f"{_prefix}{k}"
                self._flat_vars.update({flat_key: v})
        return

    def chain_str(self):
        lines = []
        for chain_item in self.chain:
            obj = chain_item.get("obj", None)
            depth = chain_item.get("depth", 0)
            indent = "  " * depth
            obj_type = type(obj).__name__
            obj_name = obj.name
            line = "{}{}: {}\n".format(indent, obj_type, obj_name)
            if obj_type == "Task":
                module_name = obj.module
                line = "{}{}: {} (module: {})\n".format(indent, obj_type, obj_name, module_name)
            lines.append(line)
        return "".join(lines)

    def copy(self):
        return Context(
            keep_obj=self.keep_obj,
            chain=copy.copy(self.chain),
            variables=copy.copy(self.variables),
            options=copy.copy(self.options),
            inventories=copy.copy(self.inventories),
            role_defaults=copy.copy(self.role_defaults),
            role_vars=copy.copy(self.role_vars),
            registered_vars=copy.copy(self.registered_vars),
        )
        # return copy.deepcopy(self)


def resolved_vars_contains(resolved_vars, new_var):
    if not isinstance(new_var, dict):
        return False
    new_var_key = new_var.get("key", "")
    if new_var_key == "":
        return False
    if not isinstance(resolved_vars, list):
        return False
    for var in resolved_vars:
        if not isinstance(var, dict):
            continue
        var_key = var.get("key", "")
        if var_key == "":
            continue
        if var_key == new_var_key:
            return True
    return False


def resolve_module_options(context: Context, taskcall: TaskCall):
    resolved_vars = []
    variables_in_loop = []
    used_variables = {}
    if len(taskcall.spec.loop) == 0:
        variables_in_loop = [{}]
    else:
        loop_key = list(taskcall.spec.loop.keys())[0]
        loop_values = taskcall.spec.loop.get(loop_key, [])
        new_var = {
            "key": loop_key,
            "value": loop_values,
            "type": VariableType.LoopVars,
        }
        if not resolved_vars_contains(resolved_vars, new_var):
            resolved_vars.append(new_var)
        if isinstance(loop_values, str):
            var_names = extract_variable_names(loop_values)
            if len(var_names) == 0:
                variables_in_loop.append({loop_key: loop_values})
            else:
                var_name = var_names[0].get("name", "")
                resolved_vars_in_item, v_type, resolve_history = context.resolve_variable(var_name)
                used_variables[var_name] = resolve_history
                new_var = {
                    "key": var_name,
                    "value": resolved_vars_in_item,
                    "type": v_type,
                }
                if not resolved_vars_contains(resolved_vars, new_var):
                    resolved_vars.append(new_var)
                if isinstance(resolved_vars_in_item, list):
                    for vi in resolved_vars_in_item:
                        variables_in_loop.append(
                            {
                                loop_key: vi,
                                "__v_type__": v_type,
                                "__v_name__": var_name,
                            }
                        )
                if isinstance(resolved_vars_in_item, dict):
                    for vi_key, vi_value in resolved_vars_in_item.items():
                        variables_in_loop.append(
                            {
                                loop_key + ".key": vi_key,
                                loop_key + ".value": vi_value,
                                "__v_type__": v_type,
                            }
                        )
                else:
                    variables_in_loop.append(
                        {
                            loop_key: resolved_vars_in_item,
                            "__v_type__": v_type,
                            "__v_name__": var_name,
                        }
                    )
        elif isinstance(loop_values, list):
            for v in loop_values:
                if isinstance(v, str) and variable_block_re.search(v):
                    var_names = extract_variable_names(v)
                    if len(var_names) == 0:
                        variables_in_loop.append({loop_key: v})
                        continue
                    var_name = var_names[0].get("name", "")
                    resolved_vars_in_item, v_type, resolve_history = context.resolve_variable(var_name)
                    used_variables[var_name] = resolve_history
                    new_var = {
                        "key": var_name,
                        "value": resolved_vars_in_item,
                        "type": v_type,
                    }
                    if not resolved_vars_contains(resolved_vars, new_var):
                        resolved_vars.append(new_var)
                    if not isinstance(resolved_vars_in_item, list):
                        variables_in_loop.append(
                            {
                                loop_key: resolved_vars_in_item,
                                "__v_type__": v_type,
                                "__v_name__": var_name,
                            }
                        )
                        continue
                    for vi in resolved_vars_in_item:
                        variables_in_loop.append(
                            {
                                loop_key: vi,
                                "__v_type__": v_type,
                                "__v_name__": var_name,
                            }
                        )
                else:
                    if isinstance(v, dict):
                        tmp_variables = {}
                        for k2, v2 in v.items():
                            key = "{}.{}".format(loop_key, k2)
                            tmp_variables.update({key: v2})
                        variables_in_loop.append(tmp_variables)
                    else:
                        variables_in_loop.append({loop_key: v})
        elif isinstance(loop_values, dict):
            tmp_variables = {}
            for k, v in loop_values.items():
                key = "{}.{}".format(loop_key, k)
                tmp_variables.update({key: v})
            variables_in_loop.append(tmp_variables)
        else:
            if loop_values:
                raise ValueError("loop_values of type {} is not supported yet".format(type(loop_values).__name__))

    resolved_opts_in_loop = []
    mutable_vars_per_mo = {}
    for variables in variables_in_loop:
        resolved_opts = None
        if isinstance(taskcall.spec.module_options, dict):
            resolved_opts = {}
            for (
                module_opt_key,
                module_opt_val,
            ) in taskcall.spec.module_options.items():
                if not isinstance(module_opt_val, str):
                    resolved_opts[module_opt_key] = module_opt_val
                    continue
                if not variable_block_re.search(module_opt_val):
                    resolved_opts[module_opt_key] = module_opt_val
                    continue
                # if variables are used in the module option value string
                var_names = extract_variable_names(module_opt_val)
                resolved_opt_val = module_opt_val
                for var_name_dict in var_names:
                    original_block = var_name_dict.get("original", "")
                    var_name = var_name_dict.get("name", "")
                    default_var_name = var_name_dict.get("default", "")
                    resolved_var_val = variables.get(var_name, None)
                    if resolved_var_val is not None:
                        loop_var_type = variables.get("__v_type__", VariableType.Unknown)
                        loop_var_name = variables.get("__v_name__", "")
                        if loop_var_type not in immutable_var_types:
                            if module_opt_key not in mutable_vars_per_mo:
                                mutable_vars_per_mo[module_opt_key] = []
                            mutable_vars_per_mo[module_opt_key].append(loop_var_name)
                    if resolved_var_val is None:
                        resolved_var_val, v_type, resolve_history = context.resolve_variable(var_name)
                        used_variables[var_name] = resolve_history
                        if resolved_var_val is not None:
                            new_var = {
                                "key": var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                            if v_type not in immutable_var_types:
                                if module_opt_key not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[module_opt_key] = []
                                mutable_vars_per_mo[module_opt_key].append(var_name)
                    if resolved_var_val is None and default_var_name != "":
                        resolved_var_val, v_type, resolve_history = context.resolve_variable(default_var_name)
                        used_variables[default_var_name] = resolve_history
                        if resolved_var_val is not None:
                            new_var = {
                                "key": default_var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                            if v_type not in immutable_var_types:
                                if module_opt_key not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[module_opt_key] = []
                                mutable_vars_per_mo[module_opt_key].append(var_name)
                    if resolved_var_val is None:
                        new_var = {
                            "key": var_name,
                            "value": None,
                            "type": v_type,
                        }
                        if not resolved_vars_contains(resolved_vars, new_var):
                            resolved_vars.append(new_var)
                        continue
                    if resolved_opt_val == original_block:
                        resolved_opt_val = resolved_var_val
                        break
                    resolved_opt_val = resolved_opt_val.replace(original_block, str(resolved_var_val))
                resolved_opts[module_opt_key] = resolved_opt_val
        elif isinstance(taskcall.spec.module_options, str):
            resolved_opt_val = taskcall.spec.module_options
            if variable_block_re.search(resolved_opt_val):
                var_names = extract_variable_names(taskcall.spec.module_options)
                for var_name_dict in var_names:
                    original_block = var_name_dict.get("original", "")
                    var_name = var_name_dict.get("name", "")
                    default_var_name = var_name_dict.get("default", "")
                    resolved_var_val = variables.get(var_name, None)
                    if resolved_var_val is not None:
                        loop_var_type = variables.get("__v_type__", VariableType.Unknown)
                        loop_var_name = variables.get("__v_name__", "")
                        if loop_var_type not in immutable_var_types:
                            if "" not in mutable_vars_per_mo:
                                mutable_vars_per_mo[""] = []
                            mutable_vars_per_mo[""].append(loop_var_name)
                    if resolved_var_val is None:
                        resolved_var_val, v_type, resolve_history = context.resolve_variable(var_name)
                        used_variables[var_name] = resolve_history
                        if resolved_var_val is not None:
                            new_var = {
                                "key": var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                            if v_type not in immutable_var_types:
                                if "" not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[""] = []
                                mutable_vars_per_mo[""].append(var_name)
                    if resolved_var_val is None and default_var_name != "":
                        resolved_var_val, v_type, resolve_history = context.resolve_variable(default_var_name)
                        used_variables[default_var_name] = resolve_history
                        if resolved_var_val is not None:
                            new_var = {
                                "key": default_var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                            if v_type not in immutable_var_types:
                                if "" not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[""] = []
                                mutable_vars_per_mo[""].append(var_name)
                    if resolved_var_val is None:
                        new_var = {
                            "key": var_name,
                            "value": None,
                            "type": v_type,
                        }
                        if not resolved_vars_contains(resolved_vars, new_var):
                            resolved_vars.append(new_var)
                        continue
                    if resolved_opt_val == original_block:
                        resolved_opt_val = resolved_var_val
                        break
                    resolved_opt_val = resolved_opt_val.replace(original_block, str(resolved_var_val))
            resolved_opts = resolved_opt_val
        else:
            resolved_opts = taskcall.spec.module_options
        resolved_opts_in_loop.append(resolved_opts)
    return resolved_opts_in_loop, resolved_vars, mutable_vars_per_mo, used_variables


def extract_variable_names(txt):
    if not variable_block_re.search(txt):
        return []
    found_var_blocks = variable_block_re.findall(txt)
    blocks = []
    for b in found_var_blocks:
        parts = b.split("|")
        var_name = ""
        default_var_name = ""
        for i, p in enumerate(parts):
            if i == 0:
                var_name = p.replace("{{", "").replace("}}", "").replace(" ", "")
                if "lookup(" in var_name and "first_found" in var_name:
                    var_name = var_name.split(",")[-1].replace(")", "")
            else:
                if "default(" in p and ")" in p:
                    default_var = p.replace("}}", "").replace("default(", "").replace(")", "").replace(" ", "")
                    if not default_var.startswith('"') and not default_var.startswith("'") and not re.compile(r"[0-9].*").match(default_var):
                        default_var_name = default_var
        tmp_b = {
            "original": b,
        }
        if var_name == "":
            continue
        tmp_b["name"] = var_name
        if default_var_name != "":
            tmp_b["default"] = default_var_name
        blocks.append(tmp_b)
    return blocks
