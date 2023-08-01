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
from pathlib import Path
import re
import os
import yaml
import traceback

try:
    # if `libyaml` is available, use C based loader for performance
    import _yaml  # noqa: F401
    from yaml import CSafeLoader as Loader
except Exception:
    # otherwise, use Python based loader
    from yaml import SafeLoader as Loader
import ansible_risk_insight.logger as logger
from .safe_glob import safe_glob
from .awx_utils import could_be_playbook, search_playbooks


module_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")

module_dir_patterns = [
    "library",
    "plugins/modules",
    "plugins/actions",
]

playbook_taskfile_dir_patterns = ["tasks", "playbooks"]


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass(frozen=True)
class TaskKeywordSet(metaclass=Singleton):
    task_keywords: set


@dataclass(frozen=True)
class BuiltinModuleSet(metaclass=Singleton):
    builtin_modules: set


p = Path(__file__).resolve().parent
with open(p / "task_keywords.txt", "r") as f:
    TaskKeywordSet(set(f.read().splitlines()))

with open(p / "builtin-modules.txt", "r") as f:
    BuiltinModuleSet(set(f.read().splitlines()))


def get_builtin_module_names():
    return BuiltinModuleSet().builtin_modules


def find_module_name(data_block):
    keys = [k for k in data_block.keys()]
    task_keywords = TaskKeywordSet().task_keywords
    builtin_modules = BuiltinModuleSet().builtin_modules
    for k in keys:
        if k.startswith("ansible.builtin"):
            return k
        if k in builtin_modules:
            return k
        if module_name_re.match(k):
            return k
    for k in keys:
        if k not in task_keywords and not k.startswith("with_"):
            return k
    return ""


def get_task_blocks(fpath="", yaml_str="", task_dict_list=None):
    d = None
    yaml_lines = ""
    if yaml_str:
        try:
            d = yaml.load(yaml_str, Loader=Loader)
            yaml_lines = yaml_str
        except Exception as e:
            logger.debug("failed to load this yaml string to get task blocks; {}".format(e.args[0]))
            return None, None
    elif fpath:
        if not os.path.exists(fpath):
            return None, None
        with open(fpath, "r") as file:
            try:
                yaml_lines = file.read()
                d = yaml.load(yaml_lines, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load this yaml file to get task blocks; {}".format(e.args[0]))
                return None, None
    elif task_dict_list is not None:
        d = task_dict_list
    else:
        return None, None
    if d is None:
        return None, None
    if not isinstance(d, list):
        return None, None
    tasks = []
    for task_dict in d:
        task_dict_loop = flatten_block_tasks(task_dict)
        tasks.extend(task_dict_loop)
    return tasks, yaml_lines


# extract all tasks by flattening block tasks recursively
# a block task like below will be flattened
# like [some_module1, some_module2, some_module3]
#
# - block:
#     - some_module1:
#     - block:
#         - some_module2
#         - some_module3
#
def flatten_block_tasks(task_dict, module_defaults={}):
    if task_dict is None:
        return []
    tasks = []

    # check module_defaults
    # if found, insert this to tasks under the block
    _module_defaults = {}
    if module_defaults and isinstance(module_defaults, dict):
        _module_defaults = module_defaults
    if "module_defaults" in task_dict:
        new_module_defaults = task_dict.get("module_defaults", {})
        if new_module_defaults and isinstance(new_module_defaults, dict):
            _module_defaults.update(new_module_defaults)

    # load normal tasks first
    if "block" in task_dict:
        tasks_in_block = task_dict.get("block", [])
        if isinstance(tasks_in_block, list):
            for t_dict in tasks_in_block:
                tasks_in_item = flatten_block_tasks(t_dict, _module_defaults)
                tasks.extend(tasks_in_item)
        else:
            tasks = [task_dict]
    else:
        tasks = [task_dict]

    # then add "rescue" block
    if "rescue" in task_dict:
        tasks_in_rescue = task_dict.get("rescue", [])
        if isinstance(tasks_in_rescue, list):
            for t_dict in tasks_in_rescue:
                tasks_in_item = flatten_block_tasks(t_dict, _module_defaults)
                tasks.extend(tasks_in_item)

    # finally add "always" block
    if "always" in task_dict:
        tasks_in_always = task_dict.get("always", [])
        if isinstance(tasks_in_always, list):
            for t_dict in tasks_in_always:
                tasks_in_item = flatten_block_tasks(t_dict, _module_defaults)
                tasks.extend(tasks_in_item)

    if _module_defaults:
        for i in range(len(tasks)):
            tasks[i]["module_defaults"] = _module_defaults

    return tasks


def search_module_files(path, module_dir_paths=[]):
    file_list = []
    # must copy the input here; otherwise, the added items are kept forever
    search_targets = [p for p in module_dir_paths]
    for module_dir_pattern in module_dir_patterns:
        search_targets.append(os.path.join(path, module_dir_pattern))
    for search_target in search_targets:
        for dirpath, folders, files in os.walk(search_target):
            for file in files:
                basename, ext = os.path.splitext(file)
                if basename == "__init__":
                    continue
                if ext == ".py" or ext == "":
                    fpath = os.path.join(dirpath, file)

                    # check if "DOCUMENTATION" is found in the file
                    skip = False
                    with open(fpath, "r") as f:
                        body = f.read()
                        if "DOCUMENTATION" not in body:
                            # if not, it is not a module file, so skip it
                            skip = True
                    if skip:
                        continue

                    file_list.append(fpath)
    file_list = sorted(file_list)
    return file_list


def find_module_dirs(role_root_dir):
    module_dirs = []
    for module_dir_pattern in module_dir_patterns:
        moddir = os.path.join(role_root_dir, module_dir_pattern)
        if os.path.exists(moddir):
            module_dirs.append(moddir)
    return module_dirs


def search_taskfiles_for_playbooks(path, taskfile_dir_paths=[]):
    # must copy the input here; otherwise, the added items are kept forever
    search_targets = [p for p in taskfile_dir_paths]
    for playbook_taskfile_dir_pattern in playbook_taskfile_dir_patterns:
        search_targets.append(os.path.join(path, playbook_taskfile_dir_pattern))
    candidates = []
    for search_target in search_targets:
        patterns = [search_target + "/**/*.ya?ml"]
        found = safe_glob(patterns, recursive=True)
        for f in found:
            # taskfiles in role will be loaded when the role is loaded, so skip
            if "/roles/" in f:
                continue
            # if it is a playbook, skip it
            if could_be_playbook(f):
                continue
            d = None
            with open(f, "r") as file:
                try:
                    d = yaml.load(file, Loader=Loader)
                except Exception as e:
                    logger.debug("failed to load this yaml file to search task" " files; {}".format(e.args[0]))
            # if d cannot be loaded as tasks yaml file, skip it
            if d is None or not isinstance(d, list):
                continue
            candidates.append(f)
    return candidates


def search_inventory_files(path):
    inventory_file_patterns = [
        os.path.join(path, "**/group_vars", "*"),
        os.path.join(path, "**/host_vars", "*"),
    ]
    files = safe_glob(patterns=inventory_file_patterns, recursive=True)
    return files


def find_best_repo_root_path(path):
    # get all possible playbooks
    playbooks = search_playbooks(path)
    # sort by directory depth to find the most top playbook
    playbooks = sorted(playbooks, key=lambda x: len(x.split(os.sep)))
    # still "repo/xxxxx/sample1.yml" may come before
    # "repo/playbooks/sample2.yml" because the depth are same,
    # so specifically put "playbooks" or "playbook" ones first
    if len(playbooks) > 0:
        most_shallow_depth = len(playbooks[0].split(os.sep))
        playbooks_ordered = []
        rests = []
        for p in playbooks:
            is_shortest = len(p.split(os.sep)) == most_shallow_depth
            is_playbook_dir = "/playbooks/" in p or "/playbook/" in p
            if is_shortest and is_playbook_dir:
                playbooks_ordered.append(p)
            else:
                rests.append(p)
        playbooks_ordered.extend(rests)
        playbooks = playbooks_ordered
    # ignore tests directory
    playbooks = [p for p in playbooks if "/tests/" not in p]
    if len(playbooks) == 0:
        raise ValueError("no playbook files found under {}".format(path))
    top_playbook_path = playbooks[0]
    root_path = ""
    if "/playbooks/" in top_playbook_path:
        root_path = top_playbook_path.split("/playbooks/")[0]
    elif "/playbook/" in top_playbook_path:
        root_path = top_playbook_path.split("/playbook/")[0]
    else:
        root_path = os.path.dirname(top_playbook_path)
    return root_path


def find_collection_name_of_repo(path):
    pattern = os.path.join(path, "**/galaxy.yml")
    found_galaxy_ymls = safe_glob(pattern, recursive=True)

    # skip galaxy ymls found in collections/roles in the repository
    _galaxy_ymls = []
    for gpath in found_galaxy_ymls:
        relative_path = gpath.replace(path, "", 1)
        if "/collections/" in relative_path:
            continue
        if "/roles/" in relative_path:
            continue
        _galaxy_ymls.append(gpath)
    found_galaxy_ymls = _galaxy_ymls

    my_collection_name = ""
    if len(found_galaxy_ymls) > 0:
        galaxy_yml = found_galaxy_ymls[0]
        my_collection_info = None
        with open(galaxy_yml, "r") as file:
            try:
                my_collection_info = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load this yaml file to read galaxy.yml; {}".format(e.args[0]))
        if my_collection_info is None:
            return ""
        namespace = my_collection_info.get("namespace", "")
        name = my_collection_info.get("name", "")
        my_collection_name = "{}.{}".format(namespace, name)
    return my_collection_name


def find_all_ymls(root_dir: str):
    patterns = [os.path.join(root_dir, "**", "*.ya?ml")]
    ymls = safe_glob(patterns)
    return ymls


def _get_body_data(body: str = "", data: list = None, fpath: str = ""):
    if fpath and not body and not data:
        try:
            with open(fpath, "r") as file:
                body = file.read()
                data = yaml.safe_load(body)
        except Exception:
            pass
    elif body and not data:
        try:
            data = yaml.safe_load(body)
        except Exception:
            pass
    return body, data, fpath


def could_be_playbook_detail(body: str = "", data: list = None, fpath: str = ""):
    body, data, fpath = _get_body_data(body, data, fpath)

    if not body:
        return False

    if len(data) == 0:
        return False

    if not isinstance(data[0], dict):
        return False

    if "hosts" in data[0]:
        return True

    if "import_playbook" in data[0] or "ansible.builtin.import_playbook" in data[0]:
        return True

    return False


def could_be_taskfile(body: str = "", data: list = None, fpath: str = ""):
    body, data, fpath = _get_body_data(body, data, fpath)

    if not body:
        return False

    if not data:
        return False

    if not isinstance(data, list):
        return False

    if not isinstance(data[0], dict):
        return False

    if "name" in data[0]:
        return True

    module_name = find_module_name(data[0])
    if module_name:
        short_module_name = module_name.split(".")[-1] if "." in module_name else module_name
        if short_module_name == "import_playbook":
            # if the found module name is import_playbook, the file is a playbook
            return False
        else:
            return True

    return False


# this function is only for empty files
# if a target file has some contents, it should be checked with
# some dedicated functions like `could_be_taskfile()`.
def label_empty_file_by_path(fpath: str):

    taskfile_dir = ["/tasks/", "/handlers/"]
    for t_d in taskfile_dir:
        if t_d in fpath:
            return "taskfile"

    playbook_dir = ["/playbooks/"]
    for p_d in playbook_dir:
        if p_d in fpath:
            return "playbook"

    return ""


def get_role_info_from_path(fpath: str):
    patterns = [
        "/roles/",
        "/tests/integration/targets/",
    ]
    targets = [
        "/tasks/",
        "/handlers/",
        "/vars/",
        "/defaults/",
        "/meta/",
    ]
    role_name = ""
    role_path = ""
    for p in patterns:
        found = False
        if p in fpath:
            relative_path = fpath.split(p, 1)[-1]
            for t in targets:
                if t in relative_path:
                    role_path = relative_path.rsplit(t, 1)[0]
                    role_name = role_path.split("/")[-1]
                    found = True
                    break
        if found:
            break
    return role_name, role_path


# TODO: implement this
def get_project_info_for_file(fpath, root_dir):
    return os.path.basename(root_dir), root_dir


def is_meta_yml(yml_path):
    parts = yml_path.split("/")
    if len(parts) > 2 and parts[-2] == "meta":
        return True
    return False


def is_vars_yml(yml_path):
    parts = yml_path.split("/")
    if len(parts) > 2 and parts[-2] in ["vars", "defaults"]:
        return True
    return False


def label_yml_file(yml_path: str, task_num_thresh: int = 50):
    body = ""
    data = None
    error = None
    try:
        with open(yml_path, "r") as file:
            body = file.read()
    except Exception:
        error = {"type": "FileReadError", "detail": traceback.format_exc()}
    if error:
        return "others", -1, error

    lines = body.splitlines()
    # roughly count tasks
    name_count = len([line for line in lines if line.lstrip().startswith("- name:")])

    if task_num_thresh > 0:
        if name_count > task_num_thresh:
            error_detail = f"The number of tasks found in yml exceeds the threshold ({task_num_thresh})"
            error = {"type": "TooManyTasksError", "detail": error_detail}
            return "others", name_count, error

    try:
        data = yaml.safe_load(body)
    except Exception:
        error = {"type": "YAMLParseError", "detail": traceback.format_exc()}
    if error:
        return "others", name_count, error

    label = ""
    if not body or not data:
        label_by_path = label_empty_file_by_path(yml_path)
        label = label_by_path if label_by_path else "others"
    elif data and not isinstance(data, list):
        label = "others"
    elif could_be_playbook(yml_path) and could_be_playbook_detail(body, data):
        label = "playbook"
    elif could_be_taskfile(body, data):
        label = "taskfile"
    else:
        label = "others"
    return label, name_count, None
