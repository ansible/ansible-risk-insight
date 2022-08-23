import argparse
import os
import re
import json
import jsonpickle
import subprocess
import logging
import copy
from dataclasses import dataclass, field
from struct5 import get_object, Repository, Playbook, Play, Role, Collection, TaskFile, Task, PlaybookFormatError, InventoryType
from resolver_fqcn import FQCNResolver


ansible_special_variables = open("ansible_variables.txt", "r").read().splitlines()
_special_var_value = "__ansible_special_variable__"
variable_block_re = re.compile(r'{{[^}]+}}')

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
    ROLE_DEFAULTS = "role_defaults"
    ROLE_VARS = "role_vars"
    REGISTERED_VARS = "registered_vars"
    SPECIAL_VARS = "special_vars"
    PARTIAL_RESOLVE = "partial_resolve"
    FAILED_TO_RESOLVE = "failed_to_resolve"

@dataclass
class Context():
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
            self.options.update(obj.options)
            self.chain.append({"obj": obj, "depth": depth_lvl})
        elif isinstance(obj, Play):
            self.variables.update(obj.variables)
            self.options.update(obj.options)
            self.chain.append({"obj": obj, "depth": depth_lvl})
        elif isinstance(obj, Role):
            self.variables.update(obj.default_variables)
            self.variables.update(obj.variables)
            for var_name in obj.default_variables:
                self.role_defaults.append(var_name)
            for var_name in obj.variables:
                self.role_vars.append(var_name)
            self.options.update(obj.options)
            self.chain.append({"obj": obj, "depth": depth_lvl})
        elif isinstance(obj, Collection):
            self.variables.update(obj.variables)
            self.options.update(obj.options)
            self.chain.append({"obj": obj, "depth": depth_lvl})
        elif isinstance(obj, TaskFile):
            self.variables.update(obj.variables)
            self.options.update(obj.options)
            self.chain.append({"obj": obj, "depth": depth_lvl})
        elif isinstance(obj, Task):
            self.variables.update(obj.variables)
            self.variables.update(obj.registered_variables)
            for var_name in obj.registered_variables:
                self.registered_vars.append(var_name)
            self.options.update(obj.options)
            self.chain.append({"obj": obj, "depth": depth_lvl})

    def resolve_variable(self, var_name):
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
                return self.resolve_single_variable(val), v_type
            elif isinstance(val, list):
                resolved_val_list = [self.resolve_single_variable(vi) for vi in val]
                return resolved_val_list, v_type
            else:
                return val, v_type

        flattened_all_variables = get_all_variables(self.variables)
        val = flattened_all_variables.get(var_name, None)
        if val is not None:
            if isinstance(val, str):
                return self.resolve_single_variable(val), v_type
            elif isinstance(val, list):
                resolved_val_list = [self.resolve_single_variable(vi) for vi in val]
                return resolved_val_list, v_type
            else:
                return val, v_type
        
        # TODO: consider group
        inventory_for_all = [iv for iv in self.inventories if iv.inventory_type==InventoryType.GROUP_VARS_TYPE and iv.name == "all"]
        for iv in inventory_for_all:
            all_variables_in_this_iv = get_all_variables(iv.variables)
            val = all_variables_in_this_iv.get(var_name, None)
            if val is not None:
                if isinstance(val, str):
                    return self.resolve_single_variable(val), v_type
                elif isinstance(val, list):
                    resolved_val_list = [self.resolve_single_variable(vi) for vi in val]
                    return resolved_val_list, v_type
                else:
                    return val, v_type

        if var_name in ansible_special_variables:
            return _special_var_value, VariableType.SPECIAL_VARS

        if var_name.startswith("hostvars[") or var_name.startswith("groups["):
            return "__partial_resolve__{}__".format(var_name), VariableType.PARTIAL_RESOLVE
        
        if "." in var_name:
            parts = var_name.split(".")
            top_var_name = parts[0]
            sub_var_name = parts[1] if len(parts) >= 2 else ""
            rest_parts = ".".join(parts[1:]) if len(parts) >= 2 else ""
            if top_var_name in self.variables or top_var_name in flattened_all_variables:
                _val, _v_type = self.resolve_variable(top_var_name)
                if _v_type == VariableType.REGISTERED_VARS:
                    return _val, _v_type
                if sub_var_name != "" and isinstance(_val, dict) and sub_var_name in _val:
                    flattened_variables = get_all_variables(_val)
                    val = flattened_variables.get(rest_parts, None)
                    if val is not None:
                        return val, _v_type

                elif sub_var_name != "" and _val is not None:
                    return "__partial_resolve__{}__".format(var_name), VariableType.PARTIAL_RESOLVE

        return None, VariableType.FAILED_TO_RESOLVE

    def resolve_single_variable(self, txt):
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
                var_val_in_txt, _ = self.resolve_variable(var_name)
                if var_val_in_txt is None and default_var_name != "":
                    var_val_in_txt, _ = self.resolve_variable(default_var_name)
                if var_val_in_txt is None:
                    return txt
                if txt == original_block:
                    return var_val_in_txt
                resolved_txt = resolved_txt.replace(original_block, str(var_val_in_txt))
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
                line = "{}{}: {} (module: {})\n".format(indent, obj_type, obj_name, module_name)
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

# TODO: support "item.key" from "with_dict"
def resolve_module_options(context, task):
    resolved_vars = []
    variables_in_loop = []
    if len(task.loop) == 0:
        variables_in_loop = [{}]
    else:
        loop_key = list(task.loop.keys())[0]
        loop_values = task.loop.get(loop_key, [])
        new_var = {"key": loop_key, "value": loop_values, "type": VariableType.NORMAL}
        if not resolved_vars_contains(resolved_vars, new_var):
            resolved_vars.append(new_var)
        if isinstance(loop_values, str):
            var_names = extract_variable_names(loop_values)
            if len(var_names) == 0:
                variables_in_loop.append({loop_key: loop_values})
            else:
                var_name = var_names[0].get("name", "")
                resolved_vars_in_item, v_type = context.resolve_variable(var_name)
                new_var = {"key": var_name, "value": resolved_vars_in_item, "type": v_type}
                if not resolved_vars_contains(resolved_vars, new_var):
                    resolved_vars.append(new_var)
                if isinstance(resolved_vars_in_item, list):
                    for vi in resolved_vars_in_item:
                        variables_in_loop.append({loop_key: vi})
                else:
                    variables_in_loop.append({loop_key: resolved_vars_in_item})  
        elif isinstance(loop_values, list):
            for v in loop_values:
                if isinstance(v, str) and variable_block_re.search(v):
                    var_names = extract_variable_names(v)
                    if len(var_names) == 0:
                        variables_in_loop.append({loop_key: v})
                        continue
                    var_name = var_names[0].get("name", "")
                    resolved_vars_in_item, v_type = context.resolve_variable(var_name)
                    new_var = {"key": var_name, "value": resolved_vars_in_item, "type": v_type}
                    if not resolved_vars_contains(resolved_vars, new_var):
                        resolved_vars.append(new_var)
                    if not isinstance(resolved_vars_in_item, list):
                        variables_in_loop.append({loop_key: resolved_vars_in_item})
                        continue
                    for vi in resolved_vars_in_item:
                        variables_in_loop.append({loop_key: vi})
                else:
                    if isinstance(v, dict):
                        tmp_variables = {}
                        for k2, v2 in v.items():
                            key = "{}.{}".format(loop_key, k2)
                            tmp_variables.update({key: v2})
                        variables_in_loop.append(tmp_variables)
                    else:
                        variables_in_loop.append({loop_key: v})
        else:
            raise ValueError("loop_values of type {} is not supported yet".format(type(loop_values).__name__))

    resolved_opts_in_loop = []
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
                    if resolved_var_val is None:
                        resolved_var_val, v_type = context.resolve_variable(var_name)
                        if resolved_var_val is not None:
                            new_var = {"key": var_name, "value": resolved_var_val, "type": v_type}
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                    if resolved_var_val is None and default_var_name != "":
                        resolved_var_val, v_type = context.resolve_variable(default_var_name)
                        if resolved_var_val is not None:
                            new_var = {"key": default_var_name, "value": resolved_var_val, "type": v_type}
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                    if resolved_var_val is None:
                        new_var = {"key": var_name, "value": None, "type": VariableType.FAILED_TO_RESOLVE}
                        if not resolved_vars_contains(resolved_vars, new_var):
                            resolved_vars.append(new_var)
                        continue
                    if resolved_opt_val == original_block:
                        resolved_opt_val = resolved_var_val
                        break
                    resolved_opt_val = resolved_opt_val.replace(original_block, str(resolved_var_val))
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
                    if resolved_var_val is None:
                        resolved_var_val, v_type = context.resolve_variable(var_name)
                        if resolved_var_val is not None:
                            new_var = {"key": var_name, "value": resolved_var_val, "type": v_type}
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                    if resolved_var_val is None and default_var_name != "":
                        resolved_var_val, v_type = context.resolve_variable(default_var_name)
                        if resolved_var_val is not None:
                            new_var = {"key": default_var_name, "value": resolved_var_val, "type": v_type}
                            if not resolved_vars_contains(resolved_vars, new_var):
                                resolved_vars.append(new_var)
                    if resolved_var_val is None:
                        new_var = {"key": var_name, "value": None, "type": VariableType.FAILED_TO_RESOLVE}
                        if not resolved_vars_contains(resolved_vars, new_var):
                            resolved_vars.append(new_var)
                        continue
                    if resolved_opt_val == original_block:
                        resolved_opt_val = resolved_var_val
                        break
                    resolved_opt_val = resolved_opt_val.replace(original_block, str(resolved_var_val))
            resolved_opts = resolved_opt_val
        else:
            resolved_opts = task.module_options
        resolved_opts_in_loop.append(resolved_opts)
    return resolved_opts_in_loop, resolved_vars


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
            else:
                if "default(" in p and ")" in p:
                    default_var = p.replace("}}", "").replace("default(", "").replace(")", "").replace(" ", "")
                    if not default_var.startswith("\"") and not default_var.startswith("'") and not re.compile(r'[0-9].*').match(default_var):
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


class CallChain():
    def __init__(self, type, name, collection, scm_repo_path, variable, path_to_dict1_json, path_to_dict2_json, json_search_root, task_name, module_name, out_dir, out_file):
        if not all and name == "":
            raise ValueError("\"name\" must be specified in order to trace the call chain")
        self.type = type.lower()
        self.name = name
        self.collection = collection
        self.scm_repo_path = ""
        self.scm_repo = None

        self.variable = variable

        self.path_to_dict1_json = path_to_dict1_json
        self.path_to_dict2_json = path_to_dict2_json

        self.module_dict = {}
        self.taskfile_dict = {}
        self.role_dict = {}
        if path_to_dict1_json != "":
            d = {}
            with open(path_to_dict1_json, "r") as file:
                d = json.load(file)
            self.module_dict = d.get("module", {})
            self.taskfile_dict = d.get("taskfile", {})
            self.role_dict = d.get("role", {})

        self.task_dict = {}
        self.playbook_dict = {}
        if path_to_dict2_json != "":
            d = {}
            with open(path_to_dict2_json, "r") as file:
                d = json.load(file)
            self.task_dict = d.get("task", {})
            self.playbook_dict = d.get("playbook", {})

        self.json_search_root = json_search_root
        self.task_name = task_name
        self.module_name = module_name
        self.out_dir = out_dir
        self.out_file = out_file

        if self.type == "playbook" and self.name != "" and self.name not in self.playbook_dict:
            playbook_dir = os.path.dirname(self.name)
            playbook_repo_root = get_git_root(playbook_dir)
            scm_repo_path = playbook_repo_root
        if scm_repo_path != "":
            repo = Repository()
            repo.load(scm_repo_path)

            self.scm_repo_path = scm_repo_path
            self.scm_repo = repo

        self.json_cache = {}

    def trace(self):
        obj = None
        found_top = None
        if self.type == "playbook":
            found_top = self.playbook_dict.get(self.name, None)
        elif self.type == "role":
            found_top = self.role_dict.get(self.name, None)
        # TODO: make collection dict
        # elif self.type == "collection":
        #     found_top = self.collection_dict.get(self.name, None)
        if found_top is None:
            if self.type == "playbook":
                obj = self.load_and_resolve_fqcn_playbook()
        else:
            json_path = self.get_json_path(found_top)
            obj = get_object(json_path=json_path, type=self.type, name=self.name, cache=self.json_cache)
        if obj is None:
            raise ValueError("failed to get object \"{}: {}\"".format(self.type, self.name))

        context_and_task = []
        base_context = Context()
        depth_lvl = 0
        base_context.add(obj, depth_lvl)
        obj_type = type(obj).__name__
        if obj_type == "Playbook":
            context_and_task = self.trace_playbook(obj, base_context, depth_lvl+1)
        elif obj_type == "Role":
            context_and_task = self.trace_role(obj, base_context, depth_lvl+1)
        elif obj_type == "Collection":
            if self.type == "role":
                role_name = self.name
                context_and_task = self.trace_role_in_collection(obj, role_name, base_context, depth_lvl+1)
            else:
                raise ValueError("not supported yet")
        output = []
        for (ctx, task) in context_and_task:
            if self.task_name != "" and task.name != self.task_name:
                continue
            if self.module_name != "" and task.resolved_name != self.module_name:
                continue
            # print("[DEBUG1] Task:", task.dump())
            # print("[DEBUG2] Context:", ctx.chain_str())
            single_item = {
                "context": ctx,
                "task": task,
            }
            if self.variable:
                resolved_options = resolve_module_options(ctx, task)
                single_item["resolved_options"] = resolved_options
                # print("[DEBUG3] resolved_options:", json.dumps(resolved_options))
            output.append(single_item)
            
        if self.out_dir != "" or self.out_file != "":
            outpath = ""
            if self.out_file != "":
                outpath = self.out_file
            elif self.out_dir != "":
                outpath = os.path.join(self.out_dir, self.name + ".json")
            json_str = jsonpickle.encode(output, make_refs=False)
            with open(outpath, "w") as file:
                file.write(json_str)

    def trace_playbook(self, playbook, context, depth_lvl):
        if not isinstance(playbook, Playbook):
            raise ValueError("this function accepts a Playbook, but got a {}".format(type(playbook).__name__))
        current_context = context.copy()
        context_and_task = []
        if "plays" in playbook.__dict__:
            for play in playbook.plays:
                current_context.add(play, depth_lvl)
                tmp_context_and_task = self.trace_play(play, current_context, depth_lvl+1)
                context_and_task.extend(tmp_context_and_task)
        else:
            for t in playbook.tasks:
                current_context.add(t, depth_lvl)
                tmp_context_and_task = self.trace_task(t, current_context, depth_lvl+1)
                context_and_task.extend(tmp_context_and_task)
            for rip in playbook.roles:
                role_fqcn = rip.resolved_name
                if role_fqcn == "":
                    continue
                role = self.get_role_by_fqcn(role_fqcn)
                if role is None:
                    continue
                current_context.add(role, depth_lvl)
                tmp_context_and_task = self.trace_role(role, current_context, depth_lvl+1)
                context_and_task.extend(tmp_context_and_task)
        return context_and_task   

    def trace_play(self, play, context, depth_lvl):
        if not isinstance(play, Play):
            raise ValueError("this function accepts a Play, but got a {}".format(type(play).__name__))
        current_context = context.copy()
        context_and_task = []
        for t in play.pre_tasks:
            current_context.add(t, depth_lvl)
            tmp_context_and_task = self.trace_task(t, current_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
        for t in play.tasks:
            current_context.add(t, depth_lvl)
            tmp_context_and_task = self.trace_task(t, current_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
        for rip in play.roles:
            role_fqcn = rip.resolved_name
            if role_fqcn == "":
                continue
            role = self.get_role_by_fqcn(role_fqcn)
            if role is None:
                continue
            current_context.add(role, depth_lvl)
            tmp_context_and_task = self.trace_role(role, current_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
        return context_and_task

    def trace_role(self, role, context, depth_lvl, main_only=True):
        if not isinstance(role, Role):
            raise ValueError("this function accepts a Role, but got a {}".format(type(role).__name__))
        current_context = context.copy()
        context_and_task = []
        for tf in role.taskfiles:
            if main_only and tf.name not in ["main.yml", "main.yaml"]:
                continue
            current_context.add(tf, depth_lvl)
            tmp_context_and_task = self.trace_taskfile(tf, current_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
        return context_and_task

    def trace_role_in_collection(self, collection, role_name, context, depth_lvl, main_only=True):
        if not isinstance(collection, Collection):
            raise ValueError("this function accepts a Collection, but got a {}".format(type(collection).__name__))
        role = None
        for r in collection.roles:
            if r.fqcn == role_name:
                role = r
                break
        if role is None:
            raise ValueError("Role \"{}\" not found in the collection \"{}\"".format(role_name, collection.name))

        return self.trace_role(role, context, depth_lvl, main_only)

    def trace_taskfile(self, taskfile, context, depth_lvl):
        if not isinstance(taskfile, TaskFile):
            raise ValueError("this function accepts a TaskFile, but got a {}".format(type(taskfile).__name__))
        current_context = context.copy()
        context_and_task = []
        for t in taskfile.tasks:
            current_context.add(t, depth_lvl)
            tmp_context_and_task = self.trace_task(t, current_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
        return context_and_task

    def trace_task(self, task, context, depth_lvl):
        if not isinstance(task, Task):
            raise ValueError("this function accepts a Task, but got a {}".format(type(task).__name__))
        current_context = context.copy()
        context_and_task = [(current_context.copy(), task)]
        if task.executable_type == "Module":
            return context_and_task
        elif task.executable_type == "TaskFile":
            taskfile_path = task.resolved_name
            if taskfile_path == "":
                return context_and_task
            taskfile = self.get_taskfile_by_path(taskfile_path)
            if taskfile is None:
                return context_and_task
            tf_context = current_context.copy()
            tf_context.add(taskfile, depth_lvl)
            tmp_context_and_task = self.trace_taskfile(taskfile, tf_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
            return context_and_task
        elif task.executable_type == "Role":
            role_fqcn = task.resolved_name
            if role_fqcn == "":
                return context_and_task
            role = self.get_role_by_fqcn(role_fqcn)
            if role is None:
                return context_and_task
            role_context = current_context.copy()
            role_context.add(role, depth_lvl)
            tmp_context_and_task = self.trace_role(role, role_context, depth_lvl+1)
            context_and_task.extend(tmp_context_and_task)
            return context_and_task
        return []

    def get_json_path(self, found_dict_item):
        json_basename = found_dict_item.get("path", "")
        if json_basename == "":
            raise ValueError("json file name is empty")
        json_path = os.path.join(self.json_search_root, json_basename)
        return json_path

    def load_and_resolve_fqcn_playbook(self):
        fpath = self.name
        if not os.path.exists(fpath):
            raise ValueError("file not found; {}".format(fpath))
        p = Playbook()
        try:
            p.load(fpath)
        except PlaybookFormatError as e:
            logging.warning("this file is not in a playbook format, maybe not a playbook file: {}".format(e.args[0]))
        except:
            logging.exception("error while loading the playbook at {}".format(fpath))

        resolver = FQCNResolver(repo_obj=self.scm_repo, path_to_dict1_json=self.path_to_dict1_json)
        p.resolve(resolver)
        with open("test_playbook.json", "w") as file:
            file.write(p.dump())
        return p

    def get_role_by_fqcn(self, role_fqcn):
        if self.scm_repo is not None:
            for r in self.scm_repo.roles:
                if r.fqcn == role_fqcn:
                    return r
        found_role = self.role_dict.get(role_fqcn, None)
        if found_role is None:
            return None
        json_path = self.get_json_path(found_role)
        role = get_object(json_path=json_path, type="role", name=role_fqcn, cache=self.json_cache)
        return role

    def get_taskfile_by_path(self, taskfile_path):
        if self.scm_repo is not None:
            for tf in self.scm_repo.taskfiles:
                if tf.defined_in == taskfile_path:
                    return tf
        found_tf = self.taskfile_dict.get(taskfile_path, None)
        if found_tf is None:
            return None
        json_path = self.get_json_path(found_tf)
        taskfile = get_object(json_path=json_path, type="taskfile", name=taskfile_path, cache=self.json_cache)
        return taskfile

def get_git_root(path):
    ret = subprocess.run(["git", "rev-parse", "--show-toplevel"], cwd=path, capture_output=True)
    if ret.returncode != 0:
        return ""
    root_path = ret.stdout.decode("utf-8").replace("\n", "")
    return root_path

def main():
    parser = argparse.ArgumentParser(
        prog='call_chain.py',
        description='trace the call chain from a playbook',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--type', default="playbook", help='the type of top object [\"playbook\", \"role\", \"collection\"]')
    parser.add_argument('-n', '--name', default="", help='the name of the top object')
    parser.add_argument('-c', '--collection', default="", help='the name of the collection')
    parser.add_argument('-s', '--scm-repo', default="", help='path to the scm repository of playbook')
    parser.add_argument('-v', '--variable', action='store_true', help='whether to resolve variables')
    parser.add_argument('-o', '--out-dir', default="", help='path to the output directory')
    parser.add_argument('--out-file', default="", help='path to the output file')
    parser.add_argument('--dict1', default="/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/dict1.json", help='path to the dict1 json')
    parser.add_argument('--dict2', default="/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/dict2.json", help='path to the dict2 json')
    parser.add_argument('--json-search-root', default="/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/galaxy_resolved", help='path to the root directory for searching json files')
    parser.add_argument('--task-name', default="", help='task name')
    parser.add_argument('--module-name', default="", help='module name')

    args = parser.parse_args()
    c = CallChain(args.type, args.name, args.collection, args.scm_repo, args.variable, args.dict1, args.dict2, args.json_search_root, args.task_name, args.module_name, args.out_dir, args.out_file)
    c.trace()


if __name__ == "__main__":
    main()