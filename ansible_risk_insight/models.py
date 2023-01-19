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

from dataclasses import dataclass, field
from typing import List, Union
from collections.abc import Callable

# from copy import deepcopy
import json
import jsonpickle
import logging
from .keyutil import (
    set_collection_key,
    set_module_key,
    set_play_key,
    set_playbook_key,
    set_repository_key,
    set_role_key,
    set_task_key,
    set_taskfile_key,
    set_call_object_key,
)

logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

# module options might be a str like below
#     community.general.ufw: port={{ item }} proto=tcp rule=allow


class PlaybookFormatError(Exception):
    pass


class TaskFormatError(Exception):
    pass


class JSONSerializable(object):
    def dump(self):
        return self.to_json()

    def to_json(self):
        return jsonpickle.encode(self, make_refs=False)

    def from_json(self, json_str):
        loaded = jsonpickle.decode(json_str)
        self.__dict__.update(loaded.__dict__)


class Resolvable(object):
    def resolve(self, resolver):
        if not hasattr(resolver, "apply"):
            raise ValueError("this resolver does not have apply() method")
        if not callable(resolver.apply):
            raise ValueError("resolver.apply is not callable")

        # apply resolver for this instance
        resolver.apply(self)

        # call resolve() for children rescursively
        targets = self.resolver_targets
        if targets is None:
            return
        for t in targets:
            if isinstance(t, str):
                continue
            t.resolve(resolver)

        # apply resolver again here
        # because some attributes was not set at first
        resolver.apply(self)
        return

    @property
    def resolver_targets(self):
        raise NotImplementedError


class LoadType:
    PROJECT = "project"
    COLLECTION = "collection"
    ROLE = "role"
    PLAYBOOK = "playbook"
    UNKNOWN = "unknown"


@dataclass
class Load(JSONSerializable):
    target_name: str = ""
    target_type: str = ""
    path: str = ""
    loader_version: str = ""
    timestamp: str = ""

    # the following variables are list of paths; not object
    roles: list = field(default_factory=list)
    playbooks: list = field(default_factory=list)
    taskfiles: list = field(default_factory=list)
    modules: list = field(default_factory=list)


@dataclass
class Object(JSONSerializable):
    type: str = ""
    key: str = ""


@dataclass
class ObjectList(JSONSerializable):
    items: list = field(default_factory=list)
    _dict: dict = field(default_factory=dict)

    def dump(self, fpath=""):
        return self.to_json(fpath=fpath)

    def to_json(self, fpath=""):
        lines = [jsonpickle.encode(obj, make_refs=False) for obj in self.items]
        json_str = "\n".join(lines)
        if fpath != "":
            open(fpath, "w").write(json_str)
        return json_str

    def to_one_line_json(self):
        return jsonpickle.encode(self.items, make_refs=False)

    def from_json(self, json_str="", fpath=""):
        if fpath != "":
            json_str = open(fpath, "r").read()
        lines = json_str.splitlines()
        items = [jsonpickle.decode(obj_str) for obj_str in lines]
        self.items = items
        self._update_dict()
        # return copy.deepcopy(self)

    # def from_json(cls, json_str="", fpath=""):
    #     if fpath != "":
    #         json_str = open(fpath, "r").read()
    #     lines = json_str.splitlines()
    #     items = [jsonpickle.decode(obj_str) for obj_str in lines]
    #     objlist = ObjectList()
    #     objlist.items = items
    #     objlist._update_dict()
    #     return objlist

    def add(self, obj, update_dict=True):
        self.items.append(obj)
        if update_dict:
            self._add_dict_item(obj)
        return

    def merge(self, obj_list):
        if not isinstance(obj_list, ObjectList):
            raise ValueError("obj_list must be an instance of ObjectList, but got {}".format(type(obj_list).__name__))
        self.items.extend(obj_list.items)
        self._update_dict()
        return

    def find_by_attr(self, key, val):
        found = [obj for obj in self.items if obj.__dict__.get(key, None) == val]
        return found

    def find_by_type(self, type):
        return [obj for obj in self.items if hasattr(obj, "type") and obj.type == type]

    def find_by_key(self, key):
        return self._dict.get(key, None)

    def contains(self, key="", obj=None):
        if obj is not None:
            key = obj.key
        return self.find_by_key(key) is not None

    def update_dict(self):
        self._update_dict()

    def _update_dict(self):
        for obj in self.items:
            self._dict[obj.key] = obj
        return

    def _add_dict_item(self, obj):
        self._dict[obj.key] = obj

    @property
    def resolver_targets(self):
        return self.items


@dataclass
class CallObject(JSONSerializable):
    type: str = ""
    key: str = ""
    called_from: str = ""
    spec: Object = field(default_factory=Object)

    @classmethod
    def from_spec(cls, spec, caller):
        instance = cls()
        instance.spec = spec
        caller_key = "None"
        if caller is not None:
            instance.called_from = caller.key
            caller_key = caller.key
        instance.key = set_call_object_key(cls.__name__, spec.key, caller_key)
        return instance


class RunTargetType:
    Playbook = "playbookcall"
    Role = "rolecall"
    Task = "taskcall"


@dataclass
class RunTarget(object):
    type: str = ""


@dataclass
class RunTargetList(object):
    items: List[RunTarget] = field(default_factory=list)

    _i: int = 0

    def __len__(self):
        return len(self.items)

    def __iter__(self):
        return self

    def __next__(self):
        if self._i == len(self.items):
            self._i = 0
            raise StopIteration()
        item = self.items[self._i]
        self._i += 1
        return item

    def __getitem__(self, i):
        return self.items[i]


@dataclass
class Module(Object, Resolvable):
    type: str = "module"
    name: str = ""
    fqcn: str = ""
    key: str = ""
    local_key: str = ""
    collection: str = ""
    role: str = ""
    defined_in: str = ""
    builtin: bool = False
    used_in: list = field(default_factory=list)  # resolved later

    annotations: dict = field(default_factory=dict)

    def set_key(self):
        set_module_key(self)

    def children_to_key(self):
        return self

    @property
    def resolver_targets(self):
        return None


@dataclass
class ModuleCall(CallObject, Resolvable):
    type: str = "modulecall"


@dataclass
class Collection(Object, Resolvable):
    type: str = "collection"
    name: str = ""
    path: str = ""
    key: str = ""
    local_key: str = ""
    metadata: dict = field(default_factory=dict)
    files: dict = field(default_factory=dict)
    playbooks: list = field(default_factory=list)
    taskfiles: list = field(default_factory=list)
    roles: list = field(default_factory=list)
    modules: list = field(default_factory=list)
    dependency: dict = field(default_factory=dict)
    requirements: dict = field(default_factory=dict)

    annotations: dict = field(default_factory=dict)

    variables: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)

    def set_key(self):
        set_collection_key(self)

    def children_to_key(self):
        module_keys = [m.key if isinstance(m, Module) else m for m in self.modules]
        self.modules = sorted(module_keys)

        playbook_keys = [p.key if isinstance(p, Playbook) else p for p in self.playbooks]
        self.playbooks = sorted(playbook_keys)

        role_keys = [r.key if isinstance(r, Role) else r for r in self.roles]
        self.roles = sorted(role_keys)

        taskfile_keys = [tf.key if isinstance(tf, TaskFile) else tf for tf in self.taskfiles]
        self.taskfiles = sorted(taskfile_keys)
        return self

    @property
    def resolver_targets(self):
        return self.playbooks + self.taskfiles + self.roles + self.modules


@dataclass
class CollectionCall(CallObject, Resolvable):
    type: str = "collectioncall"


@dataclass
class TaskCallsInTree(JSONSerializable):
    root_key: str = ""
    taskcalls: list = field(default_factory=list)


class VariableType:
    NORMAL = "normal"
    LOOP_VAR = "loop_var"
    REGISTERED_VARS = "registered_vars"
    SET_FACTS = "set_facts"
    ROLE_DEFAULTS = "role_defaults"
    ROLE_VARS = "role_vars"
    INVENTORY_VARS = "inventory_vars"
    # SPECIAL_VARS = "special_vars"
    PARTIAL_RESOLVE = "partial_resolve"
    FAILED_TO_RESOLVE = "failed_to_resolve"


mutable_types = [
    VariableType.NORMAL,
    VariableType.ROLE_DEFAULTS,
    VariableType.ROLE_VARS,
    VariableType.INVENTORY_VARS,
    VariableType.REGISTERED_VARS,
    VariableType.SET_FACTS,
    # should treat the following as mutable
    VariableType.PARTIAL_RESOLVE,
    VariableType.FAILED_TO_RESOLVE,
]


# Variable Precedence
# https://docs.ansible.com/ansible/latest/playbook_guide
#     /playbooks_variables.html#understanding-variable-precedence
@dataclass
class Variable(object):
    name: str = ""
    value: any = None
    type: VariableType = field(default_factory=VariableType)

    @property
    def is_mutable(self):
        return self.type in mutable_types


class ArgumentsType(object):
    SIMPLE = "simple"
    LIST = "list"
    DICT = "dict"


@dataclass
class Arguments(object):
    type: ArgumentsType = ""
    raw: any = None
    vars: List[Variable] = field(default_factory=list)
    resolved: bool = False
    templated: any = None
    is_mutable: bool = False

    def get(self, key: str = ""):
        sub_raw = None
        sub_templated = None
        if key == "":
            sub_raw = self.raw
            sub_templated = self.templated
        else:
            if isinstance(self.raw, dict):
                sub_raw = self.raw.get(key, None)
                sub_templated = self.templated[0].get(key, None)
            else:
                sub_raw = self.raw
                sub_templated = self.templated
        if not sub_raw:
            return None

        _vars = []
        if isinstance(sub_raw, str):
            for v in self.vars:
                if v.name in sub_raw:
                    _vars.append(v)
        is_mutable = False
        for v in _vars:
            if v.is_mutable:
                is_mutable = True
                break

        return Arguments(
            type=ArgumentsType.SIMPLE,
            raw=sub_raw,
            vars=_vars,
            resolved=self.resolved,
            templated=sub_templated,
            is_mutable=is_mutable,
        )


class LocationType:
    FILE = "file"
    DIR = "dir"
    URL = "url"


@dataclass
class Location(object):
    type: str = ""
    value: str = ""
    vars: List[Variable] = field(default_factory=list)

    _args: Arguments = None

    def __post_init__(self):
        if self._args:
            self.value = self._args.raw
            self.vars = self._args.vars

    @property
    def is_mutable(self):
        return len(self.vars) > 0

    @property
    def is_empty(self):
        return not self.type and not self.value

    def is_inside(self, loc):
        if not isinstance(loc, Location):
            raise ValueError(f"is_inside() expect Location but given {type(loc)}")
        return loc.contains(self)

    def contains(self, target, any=False, all=True):
        if isinstance(target, list):
            if any:
                return self.contains_any(target_list=target)
            elif all:
                return self.contains_all(target_list=target)
            else:
                raise ValueError('contains() must be run in either "any" or "all" mode')

        else:
            if not isinstance(target, Location):
                raise ValueError(f"contains() expect Location or list of Location, but given {type(target)}")

        my_path = self.value
        target_path = target.value
        if target_path.startswith(my_path):
            return True
        return False

    def contains_any(self, target_list):
        for target in target_list:
            if self.contains(target):
                return True
        return False

    def contains_all(self, target_list):
        count = 0
        for target in target_list:
            if self.contains(target):
                count += 1
        if count == len(target_list):
            return True
        return False


class AnnotationDetail(object):
    pass


@dataclass
class NetworkTransferDetail(AnnotationDetail):
    src: Location = None
    dest: Location = None
    is_mutable_src: bool = False
    is_mutable_dest: bool = False

    _src_arg: Arguments = None
    _dest_arg: Arguments = None

    def __post_init__(self):
        if self._src_arg:
            self.src = Location(_args=self._src_arg)
            if self._src_arg.is_mutable:
                self.is_mutable_src = True

        if self._dest_arg:
            self.dest = Location(_args=self._dest_arg)
            if self._dest_arg.is_mutable:
                self.is_mutable_dest = True


@dataclass
class InboundTransferDetail(NetworkTransferDetail):
    def __post_init__(self):
        super().__post_init__()


@dataclass
class OutboundTransferDetail(NetworkTransferDetail):
    def __post_init__(self):
        super().__post_init__()


execution_programs: list = ["sh", "bash", "zsh", "fish", "ash", "python*", "java*", "node*"]
non_execution_programs: list = ["tar", "gunzip", "unzip", "mv", "cp"]


@dataclass
class CommandExecDetail(AnnotationDetail):
    command: Arguments = None
    exec_files: List[Location] = field(default_factory=list)

    def __post_init__(self):
        self.exec_files = self.extract_exec_files()

    def extract_exec_files(self):
        cmd_str = self.command.raw
        if isinstance(cmd_str, list):
            cmd_str = " ".join(cmd_str)
        lines = cmd_str.splitlines()
        exec_files = []
        for line in lines:
            parts = []
            is_in_variable = False
            concat_p = ""
            for p in line.split(" "):
                if "{{" in p and "}}" not in p:
                    is_in_variable = True
                if "}}" in p:
                    is_in_variable = False
                concat_p += " " + p if concat_p != "" else p
                if not is_in_variable:
                    parts.append(concat_p)
                    concat_p = ""
            found_program = None
            for i, p in enumerate(parts):
                if i == 0:
                    program = p if "/" not in p else p.split("/")[-1]
                    # filter out some specific non-exec patterns
                    if program in non_execution_programs:
                        break
                    # if the command string is like "python {{ python_script_path }}",
                    # {{ python_script_path }} is the exec file instead of "python"
                    if program in execution_programs:
                        continue
                    # for the case that the program name is like "python-3.6"
                    for exec_p in execution_programs:
                        if exec_p[-1] == "*":
                            if program.startswith(exec_p[:-1]):
                                continue
                if p.startswith("-"):
                    continue
                if found_program is None:
                    found_program = p
                    break
            if found_program:
                exec_file_name = found_program
                related_vars = [v for v in self.command.vars if v.name in exec_file_name]
                location_type = LocationType.FILE
                exec_file = Location(
                    type=location_type,
                    value=exec_file_name,
                    vars=related_vars,
                )
                exec_files.append(exec_file)
        return exec_files


@dataclass
class Annotation(JSONSerializable):
    type: str = ""


@dataclass
class VariableAnnotation(Annotation):
    type: str = "variable_annotation"
    option_value: Arguments = field(default_factory=Arguments)


class RiskType:
    pass


class DefaultRiskType(RiskType):
    NONE = ""
    CMD_EXEC = "cmd_exec"
    INBOUND = "inbound_transfer"
    OUTBOUND = "outbound_transfer"
    FILE_CHANGE = "file_change"
    SYSTEM_CHANGE = "system_change"
    NETWORK_CHANGE = "network_change"
    CONFIG_CHANGE = "config_change"
    PACKAGE_INSTALL = "package_install"
    PRIVILEGE_ESCALATION = "privilege_escalation"


def equal(a: any, b: any):
    type_a = type(a)
    type_b = type(b)
    if type_a != type_b:
        return False
    if type_a == dict:
        all_keys = list(a.keys()) + list(b.keys())
        for key in all_keys:
            val_a = a.get(key, None)
            val_b = b.get(key, None)
            if not equal(val_a, val_b):
                return False
    elif type_a == list:
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            val_a = a[i]
            val_b = b[i]
            if not equal(val_a, val_b):
                return False
    else:
        if a != b:
            return False
    return True


@dataclass
class RiskAnnotation(Annotation, NetworkTransferDetail, CommandExecDetail):
    type: str = "risk_annotation"
    risk_type: RiskType = ""

    @classmethod
    def init(cls, risk_type: RiskType, detail: AnnotationDetail):
        anno = cls()
        anno.risk_type = risk_type
        for attr_name in detail.__annotations__:
            val = getattr(detail, attr_name)
            setattr(anno, attr_name, val)
        return anno

    def equal_to(self, anno):
        if self.type != anno.type:
            return False
        if self.risk_type != anno.risk_type:
            return False
        self_dict = self.__dict__
        anno_dict = anno.__dict__
        if not equal(self_dict, anno_dict):
            return False
        return True


@dataclass
class FindCondition(object):
    def check(self, anno: RiskAnnotation):
        raise NotImplementedError


@dataclass
class AnnotationCondition(object):
    type: RiskType = ""
    attr_conditions: list = field(default_factory=list)

    def risk_type(self, risk_type: RiskType):
        self.type = risk_type
        return self

    def attr(self, key: str, val: any):
        self.attr_conditions.append((key, val))
        return self


@dataclass
class AttributeCondition(FindCondition):
    attr: str = None
    result: any = None

    def check(self, anno: RiskAnnotation):
        if self.attr:
            if hasattr(anno.detail, self.attr):
                anno_value = getattr(anno.detail, self.attr)
                if anno_value == self.result:
                    return True
                if self.result is None:
                    if isinstance(anno_value, bool) and anno_value:
                        return True
        return False


@dataclass
class FunctionCondition(FindCondition):
    func: Callable = None
    args: List[any] = None
    result: any = None

    def check(self, anno: RiskAnnotation):
        if self.func:
            if callable(self.func):
                result = self.func(anno, **self.args)
                if result == self.result:
                    return True
        return False


@dataclass
class RiskAnnotationList(object):
    items: List[RiskAnnotation] = field(default_factory=list)

    _i: int = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._i == len(self.items):
            self._i = 0
            raise StopIteration()
        anno = self.items[self._i]
        self._i += 1
        return anno

    def after(self, anno: RiskAnnotation):
        return get_annotations_after(self, anno)

    def filter(self, risk_type: RiskType = ""):
        current = self
        if risk_type:
            current = filter_annotations_by_type(current, risk_type)
        return current

    def find(self, risk_type: RiskType = "", condition: Union[FindCondition, List[FindCondition]] = None):
        return search_risk_annotations(self, risk_type, condition)


def get_annotations_after(anno_list: RiskAnnotationList, anno: RiskAnnotation):
    sub_list = []
    found = False
    for anno_i in anno_list:
        if anno_i.equal_to(anno):
            found = True
        if found:
            sub_list.append(anno_i)
    if not found:
        raise ValueError(f"Annotation {anno} is not found in the specified AnnotationList")
    return RiskAnnotationList(sub_list)


def filter_annotations_by_type(anno_list: RiskAnnotationList, risk_type: RiskType):
    sub_list = []
    for anno_i in anno_list:
        if anno_i.risk_type == risk_type:
            sub_list.append(anno_i)
    return sub_list


def search_risk_annotations(anno_list: RiskAnnotationList, risk_type: RiskType = "", condition: Union[FindCondition, List[FindCondition]] = None):
    matched = []
    for risk_anno in anno_list:
        if not isinstance(risk_anno, RiskAnnotation):
            continue
        if risk_type:
            if risk_anno.risk_type != risk_type:
                continue
        if condition:
            if isinstance(condition, FindCondition):
                condition = [condition]
            for cond in condition:
                if cond.check(risk_anno):
                    matched.append(risk_anno)
                    break
    return RiskAnnotationList(matched)


class ExecutableType:
    MODULE_TYPE = "Module"
    ROLE_TYPE = "Role"
    TASKFILE_TYPE = "TaskFile"


@dataclass
class Task(Object, Resolvable):
    type: str = "task"
    name: str = ""
    module: str = ""
    index: int = -1
    play_index: int = -1
    defined_in: str = ""
    key: str = ""
    local_key: str = ""
    role: str = ""
    collection: str = ""
    variables: dict = field(default_factory=dict)
    registered_variables: dict = field(default_factory=dict)
    set_facts: dict = field(default_factory=dict)
    loop: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)
    module_options: dict = field(default_factory=dict)
    executable: str = ""
    executable_type: str = ""
    collections_in_play: list = field(default_factory=list)

    yaml_lines: str = ""
    line_num_in_file: list = field(default_factory=list)  # [begin, end]

    # FQCN for Module and Role. Or a file path for TaskFile.  resolved later
    resolved_name: str = ""
    # candidates of resovled_name
    possible_candidates: list = field(default_factory=list)

    def set_yaml_lines(self, fullpath="", task_name="", module_name="", module_options=None):
        if not module_name:
            return
        if not task_name and not module_options:
            return
        found_line_num = -1
        lines = open(fullpath, "r").read().splitlines()
        for i, line in enumerate(lines):
            if task_name and task_name in line:
                found_line_num = i
                break
            if "{}:".format(module_name) in line:
                if isinstance(module_options, str):
                    if module_options in line:
                        found_line_num = i
                        break
                elif isinstance(module_options, dict):
                    option_matched = False
                    for key in module_options:
                        if "{}:".format(key) in lines[i + 1]:
                            option_matched = True
                            break
                    if option_matched:
                        found_line_num = i
                        break
        if found_line_num < 0:
            return
        found_line = lines[found_line_num]
        is_top_of_block = found_line.replace(" ", "").startswith("-")
        begin_line_num = found_line_num
        indent_of_block = -1
        if is_top_of_block:
            indent_of_block = len(found_line.split("-")[0])
        else:
            found = False
            found_line = ""
            _indent_of_block = -1
            parts = found_line.split(" ")
            for i, p in enumerate(parts):
                if p != "":
                    break
                _indent_of_block = i + 1
            for i in range(len(lines)):
                index = begin_line_num
                _line = lines[index]
                is_top_of_block = _line.replace(" ", "").startswith("-")
                if is_top_of_block:
                    _indent = len(_line.split("-")[0])
                    if _indent < _indent_of_block:
                        found = True
                        found_line = _line
                        break
                begin_line_num -= 1
                if begin_line_num < 0:
                    break
            if not found:
                return
            indent_of_block = len(found_line.split("-")[0])
        index = begin_line_num + 1
        end_found = False
        end_line_num = -1
        for i in range(len(lines)):
            if index >= len(lines):
                break
            _line = lines[index]
            is_top_of_block = _line.replace(" ", "").startswith("-")
            if is_top_of_block:
                _indent = len(_line.split("-")[0])
                if _indent <= indent_of_block:
                    end_found = True
                    end_line_num = index - 1
                    break
            index += 1
            if index >= len(lines):
                end_found = True
                end_line_num = index
                break
        if not end_found:
            return
        if begin_line_num < 0 or end_line_num > len(lines) or begin_line_num > end_line_num:
            return
        self.yaml_lines = "\n".join(lines[begin_line_num : end_line_num + 1])
        self.line_num_in_file = [begin_line_num + 1, end_line_num + 1]
        return

    def set_key(self, parent_key="", parent_local_key=""):
        set_task_key(self, parent_key, parent_local_key)

    def children_to_key(self):
        return self

    @property
    def action(self):
        return self.executable

    @property
    def resolved_action(self):
        return self.resolved_name

    @property
    def line_number(self):
        return self.line_num_in_file

    @property
    def id(self):
        return json.dumps(
            {
                "path": self.defined_in,
                "index": self.index,
                "play_index": self.play_index,
            }
        )

    @property
    def resolver_targets(self):
        return None


@dataclass
class TaskCall(CallObject, RunTarget):
    type: str = "taskcall"
    # annotations are used for storing generic analysis data
    # any Annotators in "annotators" dir can add them to this object
    annotations: List[Annotation] = field(default_factory=list)
    args: Arguments = field(default_factory=Arguments)

    def get_annotation_by_type(self, type_str=""):
        matched = [an for an in self.annotations if an.type == type_str]
        return matched

    def get_annotation_by_type_and_attr(self, type_str="", key="", val=None):
        matched = [an for an in self.annotations if hasattr(an, "type") and an.type == type_str and getattr(an, key, None) == val]
        return matched

    def has_annotation(self, cond: AnnotationCondition):
        anno = self.get_annotation(cond)
        if anno:
            return True
        return False

    def get_annotation(self, cond: AnnotationCondition):
        _annotations = self.annotations
        if cond.type:
            _annotations = [an for an in _annotations if an.type == RiskAnnotation.type and an.risk_type == cond.type]
        if cond.attr_conditions:
            for (key, val) in cond.attr_conditions:
                _annotations = [an for an in _annotations if hasattr(an, key) and getattr(an, key) == val]
        if _annotations:
            return _annotations[0]
        return None

    @property
    def resolved_name(self):
        return self.spec.resolved_name

    @property
    def resolved_action(self):
        return self.resolved_name

    @property
    def action_type(self):
        return self.spec.executable_type


@dataclass
class AnsibleRunContext(object):
    sequence: RunTargetList = None
    root_key: str = ""

    # used by rule check
    current: RunTarget = None
    _i: int = 0

    # TODO: implement the following attributes
    vars: any = None
    host_info: any = None

    def __len__(self):
        return len(self.sequence)

    def __iter__(self):
        return self

    def __next__(self):
        if self._i == len(self.sequence):
            self._i = 0
            self.current = None
            raise StopIteration()
        t = self.sequence[self._i]
        self.current = t
        self._i += 1
        return t

    def __getitem__(self, i):
        return self.sequence[i]

    @staticmethod
    def from_tree(tree: ObjectList):
        if not tree:
            return AnsibleRunContext()
        if len(tree.items) == 0:
            return AnsibleRunContext()

        root_key = tree.items[0].spec.key
        sequence = []
        for item in tree.items:
            if not isinstance(item, RunTarget):
                continue
            sequence.append(item)
        return AnsibleRunContext(
            sequence=sequence,
            root_key=root_key,
        )

    @staticmethod
    def from_targets(targets: List[RunTarget], root_key: str = ""):
        if not root_key:
            if len(targets) > 0:
                root_key = targets[0].spec.key
        l = RunTargetList(items=targets)
        return AnsibleRunContext(sequence=l, root_key=root_key)

    def find(self, target: RunTarget):
        for t in self.sequence:
            if t.key == target.key:
                return t
        return None

    def before(self, target: RunTarget):
        targets = []
        for rt in self.sequence:
            if rt.key == target.key:
                break
            targets.append(rt)
        return AnsibleRunContext.from_targets(targets, root_key=self.root_key)

    def search(self, cond: AnnotationCondition):
        targets = [t for t in self.sequence if t.type == RunTargetType.Task and t.has_annotation(cond)]
        return AnsibleRunContext.from_targets(targets, root_key=self.root_key)

    @property
    def taskcalls(self):
        return [t for t in self.sequence if t.type == RunTargetType.Task]

    @property
    def tasks(self):
        return self.taskcalls

    @property
    def annotations(self):
        anno_list = []
        for tc in self.taskcalls:
            anno_list.extend(tc.annotations)
        return RiskAnnotationList(anno_list)


@dataclass
class TaskFile(Object, Resolvable):
    type: str = "taskfile"
    name: str = ""
    defined_in: str = ""
    key: str = ""
    local_key: str = ""
    tasks: list = field(default_factory=list)
    # role name of this task file
    # this might be empty because a task file can be defined out of roles
    role: str = ""
    collection: str = ""

    used_in: list = field(default_factory=list)  # resolved later

    annotations: dict = field(default_factory=dict)

    variables: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)

    def set_key(self):
        set_taskfile_key(self)

    def children_to_key(self):
        task_keys = [t.key if isinstance(t, Task) else t for t in self.tasks]
        self.tasks = task_keys
        return self

    @property
    def resolver_targets(self):
        return self.tasks


@dataclass
class TaskFileCall(CallObject):
    type: str = "taskfilecall"


@dataclass
class Role(Object, Resolvable):
    type: str = "role"
    name: str = ""
    defined_in: str = ""
    key: str = ""
    local_key: str = ""
    fqcn: str = ""
    metadata: dict = field(default_factory=dict)
    collection: str = ""
    playbooks: list = field(default_factory=list)
    # 1 role can have multiple task yamls
    taskfiles: list = field(default_factory=list)
    # roles/xxxx/library/zzzz.py can be called as module zzzz
    modules: list = field(default_factory=list)
    dependency: dict = field(default_factory=dict)
    requirements: dict = field(default_factory=dict)

    source: str = ""  # collection/scm repo/galaxy

    annotations: dict = field(default_factory=dict)

    default_variables: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
    # key: loop_var (default "item"), value: list/dict of item value
    loop: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)

    def set_key(self):
        set_role_key(self)

    def children_to_key(self):
        module_keys = [m.key if isinstance(m, Module) else m for m in self.modules]
        self.modules = sorted(module_keys)

        playbook_keys = [p.key if isinstance(p, Playbook) else p for p in self.playbooks]
        self.playbooks = sorted(playbook_keys)

        taskfile_keys = [tf.key if isinstance(tf, TaskFile) else tf for tf in self.taskfiles]
        self.taskfiles = sorted(taskfile_keys)
        return self

    @property
    def resolver_targets(self):
        return self.taskfiles + self.modules


@dataclass
class RoleCall(CallObject, RunTarget):
    type: str = "rolecall"


@dataclass
class RoleInPlay(Object, Resolvable):
    type: str = "roleinplay"
    name: str = ""
    options: dict = field(default_factory=dict)
    defined_in: str = ""
    role_index: int = -1
    play_index: int = -1

    role: str = ""
    collection: str = ""

    resolved_name: str = ""  # resolved later
    # candidates of resovled_name
    possible_candidates: list = field(default_factory=list)

    annotations: dict = field(default_factory=dict)
    collections_in_play: list = field(default_factory=list)

    @property
    def resolver_targets(self):
        return None


@dataclass
class RoleInPlayCall(CallObject):
    type: str = "roleinplaycall"


@dataclass
class Play(Object, Resolvable):
    type: str = "play"
    name: str = ""
    defined_in: str = ""
    index: int = -1
    key: str = ""
    local_key: str = ""

    role: str = ""
    collection: str = ""
    import_module: str = ""
    import_playbook: str = ""
    pre_tasks: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    post_tasks: list = field(default_factory=list)
    # not actual Role, but RoleInPlay defined in this playbook
    roles: list = field(default_factory=list)
    options: dict = field(default_factory=dict)
    collections_in_play: list = field(default_factory=list)
    variables: dict = field(default_factory=dict)

    def set_key(self, parent_key="", parent_local_key=""):
        set_play_key(self, parent_key, parent_local_key)

    def children_to_key(self):
        pre_task_keys = [t.key if isinstance(t, Task) else t for t in self.pre_tasks]
        self.pre_tasks = pre_task_keys

        task_keys = [t.key if isinstance(t, Task) else t for t in self.tasks]
        self.tasks = task_keys

        post_task_keys = [t.key if isinstance(t, Task) else t for t in self.post_tasks]
        self.post_tasks = post_task_keys
        return self

    @property
    def id(self):
        return json.dumps({"path": self.defined_in, "index": self.index})

    @property
    def resolver_targets(self):
        return self.pre_tasks + self.tasks + self.roles


@dataclass
class PlayCall(CallObject):
    type: str = "playcall"


@dataclass
class Playbook(Object, Resolvable):
    type: str = "playbook"
    name: str = ""
    defined_in: str = ""
    key: str = ""
    local_key: str = ""

    role: str = ""
    collection: str = ""

    plays: list = field(default_factory=list)

    used_in: list = field(default_factory=list)  # resolved later

    annotations: dict = field(default_factory=dict)

    variables: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)

    def set_key(self):
        set_playbook_key(self)

    def children_to_key(self):
        play_keys = [play.key if isinstance(play, Play) else play for play in self.plays]
        self.plays = play_keys
        return self

    @property
    def resolver_targets(self):
        if "plays" in self.__dict__:
            return self.plays
        else:
            return self.roles + self.tasks


@dataclass
class PlaybookCall(CallObject, RunTarget):
    type: str = "playbookcall"


class InventoryType:
    GROUP_VARS_TYPE = "group_vars"
    HOST_VARS_TYPE = "host_vars"
    UNKNOWN_TYPE = ""


@dataclass
class Inventory(JSONSerializable):
    type: str = "inventory"
    name: str = ""
    defined_in: str = ""
    inventory_type: str = ""
    group_name: str = ""
    host_name: str = ""
    variables: dict = field(default_factory=dict)


@dataclass
class Repository(Object, Resolvable):
    type: str = "repository"
    name: str = ""
    path: str = ""
    key: str = ""
    local_key: str = ""

    # if set, this repository is a collection repository
    my_collection_name: str = ""

    playbooks: list = field(default_factory=list)
    roles: list = field(default_factory=list)

    requirements: dict = field(default_factory=dict)

    installed_collections_path: str = ""
    installed_collections: list = field(default_factory=list)

    installed_roles_path: str = ""
    installed_roles: list = field(default_factory=list)
    modules: list = field(default_factory=list)
    taskfiles: list = field(default_factory=list)

    inventories: list = field(default_factory=list)

    version: str = ""

    annotations: dict = field(default_factory=dict)

    def set_key(self):
        set_repository_key(self)

    def children_to_key(self):
        module_keys = [m.key if isinstance(m, Module) else m for m in self.modules]
        self.modules = sorted(module_keys)

        playbook_keys = [p.key if isinstance(p, Playbook) else p for p in self.playbooks]
        self.playbooks = sorted(playbook_keys)

        taskfile_keys = [tf.key if isinstance(tf, TaskFile) else tf for tf in self.taskfiles]
        self.taskfiles = sorted(taskfile_keys)

        role_keys = [r.key if isinstance(r, Role) else r for r in self.roles]
        self.roles = sorted(role_keys)
        return self

    @property
    def resolver_targets(self):
        return self.playbooks + self.roles + self.modules + self.installed_roles + self.installed_collections


@dataclass
class RepositoryCall(CallObject):
    type: str = "repositorycall"


def call_obj_from_spec(spec: Object, caller: CallObject):
    if isinstance(spec, Repository):
        return RepositoryCall.from_spec(spec, caller)
    elif isinstance(spec, Playbook):
        return PlaybookCall.from_spec(spec, caller)
    elif isinstance(spec, Play):
        return PlayCall.from_spec(spec, caller)
    elif isinstance(spec, RoleInPlay):
        return RoleInPlayCall.from_spec(spec, caller)
    elif isinstance(spec, Role):
        return RoleCall.from_spec(spec, caller)
    elif isinstance(spec, TaskFile):
        return TaskFileCall.from_spec(spec, caller)
    elif isinstance(spec, Task):
        return TaskCall.from_spec(spec, caller)
    elif isinstance(spec, Module):
        return ModuleCall.from_spec(spec, caller)
    return None


# inherit Repository just for convenience
# this is not a Repository but one or multiple Role / Collection
@dataclass
class GalaxyArtifact(Repository):
    type: str = ""  # Role or Collection

    # make it easier to search a module
    module_dict: dict = field(default_factory=dict)
    # make it easier to search a task
    task_dict: dict = field(default_factory=dict)
    # make it easier to search a taskfile
    taskfile_dict: dict = field(default_factory=dict)
    # make it easier to search a role
    role_dict: dict = field(default_factory=dict)
    # make it easier to search a playbook
    playbook_dict: dict = field(default_factory=dict)
    # make it easier to search a collection
    collection_dict: dict = field(default_factory=dict)
