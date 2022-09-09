import os
import re
import copy
from dataclasses import dataclass, field
from models import (
    Playbook,
    Play,
    Role,
    Collection,
    TaskFile,
    Task,
    InventoryType,
)


ansible_special_variables = (
    open("ansible_variables.txt", "r").read().splitlines()
)
_special_var_value = "__ansible_special_variable__"
variable_block_re = re.compile(r"{{[^}]+}}")


class VariableType:
    NORMAL = "normal"
    LOOP_VAR = "loop_var"
    REGISTERED_VARS = "registered_vars"
    ROLE_DEFAULTS = "role_defaults"
    ROLE_VARS = "role_vars"
    INVENTORY_VARS = "inventory_vars"
    SPECIAL_VARS = "special_vars"
    PARTIAL_RESOLVE = "partial_resolve"
    FAILED_TO_RESOLVE = "failed_to_resolve"


mutable_types = [
    VariableType.NORMAL,
    VariableType.ROLE_DEFAULTS,
    VariableType.ROLE_VARS,
    VariableType.INVENTORY_VARS,
]


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
        r = Role()
        r.from_json(json_str)
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


def get_all_variables(var_dict={}):
    def _recursive_extract(name, node):
        all_vars = {}
        if isinstance(node, dict):
            for k, v in node.items():
                var_name = "{}.{}".format(name, k) if name != "" else k
                all_vars[var_name] = v
                child_node_vars = _recursive_extract(var_name, v)
                all_vars.update(child_node_vars)
        else:
            var_name = name
            all_vars[var_name] = node
        return all_vars

    all_vars = _recursive_extract("", var_dict)
    return all_vars


class VariableType:
    NORMAL = "normal"
    LOOP_VAR = "loop_var"
    REGISTERED_VARS = "registered_vars"
    ROLE_DEFAULTS = "role_defaults"
    ROLE_VARS = "role_vars"
    INVENTORY_VARS = "inventory_vars"
    SPECIAL_VARS = "special_vars"
    PARTIAL_RESOLVE = "partial_resolve"
    FAILED_TO_RESOLVE = "failed_to_resolve"


mutable_types = [
    VariableType.NORMAL,
    VariableType.ROLE_DEFAULTS,
    VariableType.ROLE_VARS,
    VariableType.INVENTORY_VARS,
]


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

    def add(self, obj, depth_lvl=0):
        if isinstance(obj, Playbook):
            self.variables.update(obj.variables)
        elif isinstance(obj, Play):
            self.variables.update(obj.variables)
        elif isinstance(obj, Role):
            self.variables.update(obj.default_variables)
            self.variables.update(obj.variables)
            for var_name in obj.default_variables:
                self.role_defaults.append(var_name)
            for var_name in obj.variables:
                self.role_vars.append(var_name)
        elif isinstance(obj, Collection):
            self.variables.update(obj.variables)
        elif isinstance(obj, TaskFile):
            self.variables.update(obj.variables)
        elif isinstance(obj, Task):
            self.variables.update(obj.variables)
            self.variables.update(obj.registered_variables)
            for var_name in obj.registered_variables:
                self.registered_vars.append(var_name)
        else:
            # Module
            return
        self.options.update(obj.options)
        chain_node = {"key": obj.key, "depth": depth_lvl}
        if self.keep_obj:
            chain_node["obj"] = obj
        self.chain.append(chain_node)

    def resolve_variable(self, var_name, resolve_history=[]):
        if var_name in resolve_history:
            return None, VariableType.FAILED_TO_RESOLVE
        _resolve_history = [rn for rn in resolve_history] + [var_name]

        v_type = VariableType.NORMAL
        if var_name in self.role_vars:
            v_type = VariableType.ROLE_VARS
        elif var_name in self.role_defaults:
            v_type = VariableType.ROLE_DEFAULTS
        elif var_name in self.registered_vars:
            v_type = VariableType.REGISTERED_VARS

        val = self.variables.get(var_name, None)
        if val is not None:
            if isinstance(val, str):
                return (
                    self.resolve_single_variable(val, _resolve_history),
                    v_type,
                )
            elif isinstance(val, list):
                resolved_val_list = [
                    self.resolve_single_variable(vi, _resolve_history)
                    for vi in val
                ]
                return resolved_val_list, v_type
            else:
                return val, v_type

        flattened_all_variables = get_all_variables(self.variables)
        val = flattened_all_variables.get(var_name, None)
        if val is not None:
            if isinstance(val, str):
                return (
                    self.resolve_single_variable(val, _resolve_history),
                    v_type,
                )
            elif isinstance(val, list):
                resolved_val_list = [
                    self.resolve_single_variable(vi, _resolve_history)
                    for vi in val
                ]
                return resolved_val_list, v_type
            else:
                return val, v_type

        # TODO: consider group
        inventory_for_all = [
            iv
            for iv in self.inventories
            if iv.inventory_type == InventoryType.GROUP_VARS_TYPE
            and iv.name == "all"
        ]
        for iv in inventory_for_all:
            all_variables_in_this_iv = get_all_variables(iv.variables)
            val = all_variables_in_this_iv.get(var_name, None)
            if val is not None:
                v_type = VariableType.INVENTORY_VARS
                if isinstance(val, str):
                    return (
                        self.resolve_single_variable(val, _resolve_history),
                        v_type,
                    )
                elif isinstance(val, list):
                    resolved_val_list = [
                        self.resolve_single_variable(vi, _resolve_history)
                        for vi in val
                    ]
                    return resolved_val_list, v_type
                else:
                    return val, v_type

        if var_name in ansible_special_variables:
            return _special_var_value, VariableType.SPECIAL_VARS

        if var_name.startswith("hostvars[") or var_name.startswith("groups["):
            return (
                "__partial_resolve__{}__".format(var_name),
                VariableType.PARTIAL_RESOLVE,
            )

        if "." in var_name:
            parts = var_name.split(".")
            top_var_name = parts[0]
            sub_var_name = parts[1] if len(parts) >= 2 else ""
            rest_parts = ".".join(parts[1:]) if len(parts) >= 2 else ""
            if (
                top_var_name in self.variables
                or top_var_name in flattened_all_variables
            ):
                _val, _v_type = self.resolve_variable(
                    top_var_name, _resolve_history
                )
                if _v_type == VariableType.REGISTERED_VARS:
                    return _val, _v_type
                if (
                    sub_var_name != ""
                    and isinstance(_val, dict)
                    and sub_var_name in _val
                ):
                    flattened_variables = get_all_variables(_val)
                    val = flattened_variables.get(rest_parts, None)
                    if val is not None:
                        return val, _v_type

                elif sub_var_name != "" and _val is not None:
                    return (
                        "__partial_resolve__{}__".format(var_name),
                        VariableType.PARTIAL_RESOLVE,
                    )

        return None, VariableType.FAILED_TO_RESOLVE

    def resolve_single_variable(self, txt, resolve_history=[]):
        if not isinstance(txt, str):
            return txt
        if "{{" in txt:
            var_names_in_txt = extract_variable_names(txt)
            if len(var_names_in_txt) == 0:
                return txt
            resolved_txt = txt
            for var_name_in_txt in var_names_in_txt:
                original_block = var_name_in_txt.get("original", "")
                var_name = var_name_in_txt.get("name", "")
                default_var_name = var_name_in_txt.get("default", "")
                var_val_in_txt, _ = self.resolve_variable(
                    var_name, resolve_history
                )
                if var_val_in_txt is None and default_var_name != "":
                    var_val_in_txt, _ = self.resolve_variable(
                        default_var_name, resolve_history
                    )
                if var_val_in_txt is None:
                    return txt
                if txt == original_block:
                    return var_val_in_txt
                resolved_txt = resolved_txt.replace(
                    original_block, str(var_val_in_txt)
                )
            return resolved_txt
        else:
            return txt

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
                line = "{}{}: {} (module: {})\n".format(
                    indent, obj_type, obj_name, module_name
                )
            lines.append(line)
        return "".join(lines)

    def copy(self):
        return copy.deepcopy(self)


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


def resolve_module_options(context, task):
    resolved_vars = []
    variables_in_loop = []
    if len(task.loop) == 0:
        variables_in_loop = [{}]
    else:
        loop_key = list(task.loop.keys())[0]
        loop_values = task.loop.get(loop_key, [])
        new_var = {
            "key": loop_key,
            "value": loop_values,
            "type": VariableType.LOOP_VAR,
        }
        if not resolved_vars_contains(resolved_vars, new_var):
            resolved_vars.append(new_var)
        if isinstance(loop_values, str):
            var_names = extract_variable_names(loop_values)
            if len(var_names) == 0:
                variables_in_loop.append({loop_key: loop_values})
            else:
                var_name = var_names[0].get("name", "")
                resolved_vars_in_item, v_type = context.resolve_variable(
                    var_name
                )
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
                    resolved_vars_in_item, v_type = context.resolve_variable(
                        var_name
                    )
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
            raise ValueError(
                "loop_values of type {} is not supported yet".format(
                    type(loop_values).__name__
                )
            )

    resolved_opts_in_loop = []
    mutable_vars_per_mo = {}
    for variables in variables_in_loop:
        resolved_opts = None
        if isinstance(task.module_options, dict):
            resolved_opts = {}
            for module_opt_key, module_opt_val in task.module_options.items():
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
                        loop_var_type = variables.get("__v_type__", "")
                        loop_var_name = variables.get("__v_name__", "")
                        if loop_var_type in mutable_types:
                            if module_opt_key not in mutable_vars_per_mo:
                                mutable_vars_per_mo[module_opt_key] = []
                            mutable_vars_per_mo[module_opt_key].append(
                                loop_var_name
                            )
                    if resolved_var_val is None:
                        resolved_var_val, v_type = context.resolve_variable(
                            var_name
                        )
                        if resolved_var_val is not None:
                            new_var = {
                                "key": var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(
                                resolved_vars, new_var
                            ):
                                resolved_vars.append(new_var)
                            if v_type in mutable_types:
                                if module_opt_key not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[module_opt_key] = []
                                mutable_vars_per_mo[module_opt_key].append(
                                    var_name
                                )
                    if resolved_var_val is None and default_var_name != "":
                        resolved_var_val, v_type = context.resolve_variable(
                            default_var_name
                        )
                        if resolved_var_val is not None:
                            new_var = {
                                "key": default_var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(
                                resolved_vars, new_var
                            ):
                                resolved_vars.append(new_var)
                            if v_type in mutable_types:
                                if module_opt_key not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[module_opt_key] = []
                                mutable_vars_per_mo[module_opt_key].append(
                                    var_name
                                )
                    if resolved_var_val is None:
                        new_var = {
                            "key": var_name,
                            "value": None,
                            "type": VariableType.FAILED_TO_RESOLVE,
                        }
                        if not resolved_vars_contains(resolved_vars, new_var):
                            resolved_vars.append(new_var)
                        continue
                    if resolved_opt_val == original_block:
                        resolved_opt_val = resolved_var_val
                        break
                    resolved_opt_val = resolved_opt_val.replace(
                        original_block, str(resolved_var_val)
                    )
                resolved_opts[module_opt_key] = resolved_opt_val
        elif isinstance(task.module_options, str):
            resolved_opt_val = task.module_options
            if variable_block_re.search(resolved_opt_val):
                var_names = extract_variable_names(task.module_options)
                for var_name_dict in var_names:
                    original_block = var_name_dict.get("original", "")
                    var_name = var_name_dict.get("name", "")
                    default_var_name = var_name_dict.get("default", "")
                    resolved_var_val = variables.get(var_name, None)
                    if resolved_var_val is not None:
                        loop_var_type = variables.get("__v_type__", "")
                        loop_var_name = variables.get("__v_name__", "")
                        if loop_var_type in mutable_types:
                            if "" not in mutable_vars_per_mo:
                                mutable_vars_per_mo[""] = []
                            mutable_vars_per_mo[""].append(loop_var_name)
                    if resolved_var_val is None:
                        resolved_var_val, v_type = context.resolve_variable(
                            var_name
                        )
                        if resolved_var_val is not None:
                            new_var = {
                                "key": var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(
                                resolved_vars, new_var
                            ):
                                resolved_vars.append(new_var)
                            if v_type in mutable_types:
                                if "" not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[""] = []
                                mutable_vars_per_mo[""].append(var_name)
                    if resolved_var_val is None and default_var_name != "":
                        resolved_var_val, v_type = context.resolve_variable(
                            default_var_name
                        )
                        if resolved_var_val is not None:
                            new_var = {
                                "key": default_var_name,
                                "value": resolved_var_val,
                                "type": v_type,
                            }
                            if not resolved_vars_contains(
                                resolved_vars, new_var
                            ):
                                resolved_vars.append(new_var)
                            if v_type in mutable_types:
                                if "" not in mutable_vars_per_mo:
                                    mutable_vars_per_mo[""] = []
                                mutable_vars_per_mo[""].append(var_name)
                    if resolved_var_val is None:
                        new_var = {
                            "key": var_name,
                            "value": None,
                            "type": VariableType.FAILED_TO_RESOLVE,
                        }
                        if not resolved_vars_contains(resolved_vars, new_var):
                            resolved_vars.append(new_var)
                        continue
                    if resolved_opt_val == original_block:
                        resolved_opt_val = resolved_var_val
                        break
                    resolved_opt_val = resolved_opt_val.replace(
                        original_block, str(resolved_var_val)
                    )
            resolved_opts = resolved_opt_val
        else:
            resolved_opts = task.module_options
        resolved_opts_in_loop.append(resolved_opts)
    return resolved_opts_in_loop, resolved_vars, mutable_vars_per_mo


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
                var_name = (
                    p.replace("{{", "").replace("}}", "").replace(" ", "")
                )
            else:
                if "default(" in p and ")" in p:
                    default_var = (
                        p.replace("}}", "")
                        .replace("default(", "")
                        .replace(")", "")
                        .replace(" ", "")
                    )
                    if (
                        not default_var.startswith('"')
                        and not default_var.startswith("'")
                        and not re.compile(r"[0-9].*").match(default_var)
                    ):
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
