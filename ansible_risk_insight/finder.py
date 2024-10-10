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
import json
import yaml
import traceback
from ansible_risk_insight.yaml_utils import FormattedYAML

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


fqcn_module_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")
module_name_re = re.compile(r"^[a-z0-9_.]+$")
taskfile_path_in_role_re = r".*roles/[^/]+/(tasks|handlers)/.*\.ya?ml"

module_dir_patterns = [
    "library",
    "plugins/modules",
    "plugins/actions",
]

playbook_taskfile_dir_patterns = ["tasks", "playbooks"]

github_workflows_dir = ".github/workflows"


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
        if type(k) is not str:
            continue
        if k.startswith("ansible.builtin"):
            return k
        if k in builtin_modules:
            return k
        if fqcn_module_name_re.match(k):
            return k
    for k in keys:
        if type(k) is not str:
            continue
        if k in task_keywords:
            continue
        if k.startswith("with_"):
            continue
        if module_name_re.match(k):
            return k
    if "local_action" in keys:
        local_action_value = data_block["local_action"]
        module_name = ""
        if isinstance(local_action_value, str):
            module_name = local_action_value.split(" ")[0]
        elif isinstance(local_action_value, dict):
            module_name = local_action_value.get("module", "")
        if module_name:
            return module_name
    return ""


def get_task_blocks(
    fpath="",
    yaml_str="",
    task_dict_list=None,
    jsonpath_prefix="",
):
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
    for i, task_dict in enumerate(d):
        jsonpath = f"{jsonpath_prefix}.{i}"
        task_dict_loop = flatten_block_tasks(task_dict=task_dict, jsonpath_prefix=jsonpath)
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
def flatten_block_tasks(task_dict, jsonpath_prefix="", module_defaults={}):
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
        task_jsonpath = jsonpath_prefix + ".block"
        tasks_in_block = task_dict.get("block", [])
        if isinstance(tasks_in_block, list):
            for i, t_dict in enumerate(tasks_in_block):
                _current_prefix = task_jsonpath + f".{i}"
                tasks_in_item = flatten_block_tasks(t_dict, _current_prefix, _module_defaults)
                tasks.extend(tasks_in_item)
        else:
            tasks = [(task_dict, task_jsonpath)]
    else:
        task_jsonpath = jsonpath_prefix
        tasks = [(task_dict, task_jsonpath)]

    # then add "rescue" block
    if "rescue" in task_dict:
        task_jsonpath = jsonpath_prefix + ".rescue"
        tasks_in_rescue = task_dict.get("rescue", [])
        if isinstance(tasks_in_rescue, list):
            for i, t_dict in enumerate(tasks_in_rescue):
                _current_prefix = task_jsonpath + f".{i}"
                tasks_in_item = flatten_block_tasks(t_dict, _current_prefix, _module_defaults)
                tasks.extend(tasks_in_item)

    # finally add "always" block
    if "always" in task_dict:
        task_jsonpath = jsonpath_prefix + ".always"
        tasks_in_always = task_dict.get("always", [])
        if isinstance(tasks_in_always, list):
            for i, t_dict in enumerate(tasks_in_always):
                _current_prefix = task_jsonpath + f".{i}"
                tasks_in_item = flatten_block_tasks(t_dict, _current_prefix, _module_defaults)
                tasks.extend(tasks_in_item)

    return tasks


def identify_lines_with_jsonpath(fpath: str = "", yaml_str: str = "", jsonpath: str = "") -> tuple[str, tuple[int, int]]:
    if not jsonpath:
        return None, None

    d = None
    yaml_lines = ""
    if yaml_str:
        try:
            d = yaml.load(yaml_str, Loader=Loader)
            yaml_lines = yaml_str
        except Exception as e:
            logger.debug("failed to load this yaml string to identify lines; {}".format(e.args[0]))
            return None, None
    elif fpath:
        if not os.path.exists(fpath):
            return None, None
        with open(fpath, "r") as file:
            try:
                yaml_lines = file.read()
                d = yaml.load(yaml_lines, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load this yaml file to identify lines; {}".format(e.args[0]))
                return None, None
    if not d:
        return None, None

    path_parts = jsonpath.strip(".").split(".")
    current_lines = yaml_lines
    current_line_num = 1
    line_num_tuple = None
    for p in path_parts:
        if p == "plays":
            pass
        elif p in ["pre_tasks", "tasks", "post_tasks", "handlers", "block", "rescue", "always"]:
            blocks = find_child_yaml_block(current_lines, key=p, line_num_offset=current_line_num)
            current_lines, line_num_tuple = blocks[0]
            current_line_num = line_num_tuple[0]
        else:
            try:
                p_num = int(p)
                blocks = find_child_yaml_block(current_lines, line_num_offset=current_line_num)
                current_lines, line_num_tuple = blocks[p_num]
                current_line_num = line_num_tuple[0]
            except Exception as e:
                logger.debug(f"error occurred while detecting line number: {e}")
                pass
    return current_lines, line_num_tuple


def find_child_yaml_block(yaml_str: str, key: str = "", line_num_offset: int = -1) -> list:
    skip_condition_funcs = [
        # for YAML separator
        lambda x: x.strip() == "---",
        # for empty line
        lambda x: x.strip() == "",
        # for comment line
        lambda x: x.strip().startswith("#"),
    ]

    def match_condition_func(x):
        if key:
            return x.strip().startswith(f"{key}:")
        else:
            return x.strip().startswith("- ")

    def is_yaml_end_separator(x):
        return x.strip() == "..."

    def get_indent_level(x):
        return len(x) - len(x.lstrip())

    top_level_indent = 100
    for line in yaml_str.splitlines():
        skip = False
        for skip_cond_func in skip_condition_funcs:
            if skip_cond_func(line):
                skip = True
                break
        if skip:
            continue
        if match_condition_func(line):
            current_indent = get_indent_level(line)
            if current_indent < top_level_indent:
                top_level_indent = current_indent
    if top_level_indent == 100:
        return []

    blocks = []
    line_buffer = []
    isolated_line_buffer = []
    buffer_begin = -1
    if key:
        for i, line in enumerate(yaml_str.splitlines()):
            line_num = i + 1
            current_indent = get_indent_level(line)
            if current_indent == top_level_indent:
                if line_buffer and not blocks:
                    block_str = "\n".join(line_buffer)
                    begin = buffer_begin
                    end = line_num - 1
                    if line_num_offset > 0:
                        begin += line_num_offset - 1
                        end += line_num_offset - 1
                    line_num_tuple = (begin, end)
                    blocks.append((block_str, line_num_tuple))
                if match_condition_func(line):
                    buffer_begin = line_num + 1
            if buffer_begin > 0 and line_num >= buffer_begin:
                line_buffer.append(line)
        if line_buffer and not blocks:
            block_str = "\n".join(line_buffer)
            begin = buffer_begin
            end = line_num
            if line_num_offset > 0:
                begin += line_num_offset - 1
                end += line_num_offset - 1
            line_num_tuple = (begin, end)
            blocks.append((block_str, line_num_tuple))
    else:
        for i, line in enumerate(yaml_str.splitlines()):
            line_num = i + 1
            current_indent = get_indent_level(line)
            new_block = False
            if current_indent == top_level_indent and match_condition_func(line):
                skip = False
                for skip_cond_func in skip_condition_funcs:
                    if skip_cond_func(line):
                        skip = True
                        break
                if not skip:
                    new_block = True
            if new_block:
                if line_buffer:
                    block_str = ""
                    block_str += "\n".join(line_buffer)
                    begin = buffer_begin
                    end = line_num - 1
                    if line_num_offset > 0:
                        begin += line_num_offset - 1
                        end += line_num_offset - 1
                    line_num_tuple = (begin, end)
                    blocks.append((block_str, line_num_tuple))
                    line_buffer = []
                    isolated_line_buffer = []
                buffer_begin = line_num
                line_buffer.append(line)
            else:
                if buffer_begin < 0:
                    isolated_line_buffer.append(line)
                else:
                    line_buffer.append(line)
        if line_buffer:
            block_str = ""
            block_str += "\n".join(line_buffer)
            begin = buffer_begin
            end = line_num
            if is_yaml_end_separator(line_buffer[-1]):
                end = line_num - 1
            if line_num_offset > 0:
                begin += line_num_offset - 1
                end += line_num_offset - 1
            line_num_tuple = (begin, end)
            blocks.append((block_str, line_num_tuple))
    return blocks


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


def search_taskfiles_for_playbooks(path, taskfile_dir_paths: list = []):
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
            if re.match(taskfile_path_in_role_re, f):
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
    base_path = path

    manifest_json_path = os.path.join(base_path, "MANIFEST.json")
    galaxy_yml_path = os.path.join(base_path, "galaxy.yml")
    meta_main_yml_path = os.path.join(base_path, "meta/main.yml")
    if os.path.exists(manifest_json_path) or os.path.exists(galaxy_yml_path) or os.path.exists(meta_main_yml_path):
        return base_path

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
    top_playbook_relative_path = top_playbook_path[len(base_path) :]
    root_path = ""
    if "/playbooks/" in top_playbook_relative_path:
        root_path = top_playbook_path.rsplit("/playbooks/", 1)[0]
    elif "/playbook/" in top_playbook_relative_path:
        root_path = top_playbook_path.rsplit("/playbook/", 1)[0]
    else:
        root_path = os.path.dirname(top_playbook_path)

    # if the root_path is a subdirectory of the input path,
    # then try finding more appropriate root dir based on `roles`
    if path != root_path:
        pattern = os.path.join(path, "**", "roles")
        found_roles = safe_glob(pattern, recursive=True)
        if found_roles:
            roles_dir = found_roles[0]
            candidate = os.path.dirname(roles_dir)
            if len(candidate) < len(root_path):
                root_path = candidate

    return root_path


def find_collection_name_of_repo(path):
    galaxy_yml_pattern = os.path.join(path, "**/galaxy.yml")
    manifest_json_pattern = os.path.join(path, "**/MANIFEST.json")
    found_metadata_files = safe_glob([galaxy_yml_pattern, manifest_json_pattern], recursive=True)
    found_metadata_files = [fpath for fpath in found_metadata_files if github_workflows_dir not in fpath]

    # skip metadata files found in collections/roles in the repository
    _metadata_files = []
    for mpath in found_metadata_files:
        relative_path = mpath.replace(path, "", 1)
        if "/collections/" in relative_path:
            continue
        if "/roles/" in relative_path:
            continue
        _metadata_files.append(mpath)
    found_metadata_files = _metadata_files

    my_collection_name = ""
    if len(found_metadata_files) > 0:
        metadata_file = found_metadata_files[0]
        my_collection_info = None
        if metadata_file.endswith(".yml"):
            with open(metadata_file, "r") as file:
                try:
                    my_collection_info = yaml.load(file, Loader=Loader)
                except Exception as e:
                    logger.debug("failed to load this yaml file to read galaxy.yml; {}".format(e.args[0]))
        elif metadata_file.endswith(".json"):
            with open(metadata_file, "r") as file:
                try:
                    my_collection_info = json.load(file).get("collection_info", {})
                except Exception as e:
                    logger.debug("failed to load this json file to read MANIFEST.json; {}".format(e.args[0]))
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


def find_all_files(root_dir: str):
    patterns = [os.path.join(root_dir, "**", "*")]
    files = safe_glob(patterns, type="file")
    return files


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

    if not data:
        return False

    if not isinstance(data, list):
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
        "/tests/",
    ]
    # use alternative target if it matches
    # e.g.) tests/integration/targets/xxxx/playbooks/tasks/included.yml
    #        --> role_name should be `xxxx`, not `playbooks`
    alternative_targets = {
        "/tasks/": [
            "/playbooks/tasks/",
        ],
        "/vars/": [
            "/playbooks/vars/",
        ],
    }
    role_name = ""
    role_path = ""
    for p in patterns:
        found = False
        if p in fpath:
            parent_dir = fpath.split(p, 1)[0]
            relative_path = os.path.join(p, fpath.split(p, 1)[-1])
            if relative_path[0] == "/":
                relative_path = relative_path[1:]
            for t in targets:
                if t in relative_path:
                    _target = t

                    _alt_targets = alternative_targets.get(t, [])
                    for at in _alt_targets:
                        if at in relative_path:
                            _target = at
                            break

                    _path = relative_path.rsplit(_target, 1)[0]
                    role_name = _path.split("/")[-1]

                    # if the path is something like "xxxx/roles/tasks"
                    # it is not an actual role, so skip it
                    if role_name == p.strip("/"):
                        continue

                    role_path = os.path.join(parent_dir, _path)
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


def count_top_level_element(yml_body: str = ""):
    def _is_skip_line(line: str):
        # skip empty line
        if not line.strip():
            return True
        # skip comment line
        if line.strip()[0] == "#":
            return True
        return False

    lines = yml_body.splitlines()
    top_level_indent = 1024
    valid_line_found = False
    for line in lines:
        if _is_skip_line(line):
            continue

        valid_line_found = True
        indent_level = len(line) - len(line.lstrip())
        if indent_level < top_level_indent:
            top_level_indent = indent_level

    if not valid_line_found:
        return -1

    count = 0
    for line in lines:
        if _is_skip_line(line):
            continue
        if len(line) < top_level_indent:
            continue
        elem = line[top_level_indent:]
        if not elem:
            continue
        if elem[0] == " ":
            continue
        else:
            count += 1
    return count


def label_yml_file(yml_path: str = "", yml_body: str = "", task_num_thresh: int = 50):
    body = ""
    data = None
    error = None
    if yml_body:
        body = yml_body
    elif not yml_body and yml_path:
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
            error_detail = f"The number of task names found in yml exceeds the threshold ({task_num_thresh})"
            error = {"type": "TooManyTasksError", "detail": error_detail}
            return "others", name_count, error

    top_level_element_count = count_top_level_element(body)
    if task_num_thresh > 0:
        if top_level_element_count > task_num_thresh:
            error_detail = f"The number of top-level elements found in yml exceeds the threshold ({task_num_thresh})"
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
        label_by_path = ""
        if yml_path:
            label_by_path = label_empty_file_by_path(yml_path)
        label = label_by_path if label_by_path else "others"
    elif data and not isinstance(data, list):
        label = "others"
    elif could_be_playbook_detail(body, data):
        label = "playbook"
    elif could_be_taskfile(body, data):
        label = "taskfile"
    else:
        label = "others"
    return label, name_count, None


def get_yml_label(file_path, root_path, task_num_threshold: int = -1):
    relative_path = file_path.replace(root_path, "")
    if relative_path[-1] == "/":
        relative_path = relative_path[:-1]

    label, _, error = label_yml_file(file_path, task_num_thresh=task_num_threshold)
    role_name, role_path = get_role_info_from_path(file_path)
    role_info = None
    if role_name and role_path:
        role_info = {"name": role_name, "path": role_path}

    project_name, project_path = get_project_info_for_file(file_path, root_path)
    project_info = None
    if project_name and project_path:
        project_info = {"name": project_name, "path": project_path}

    # print(f"[{label}] {relative_path} {role_info}")
    if error:
        logger.debug(f"failed to get yml label:\n {error}")
        label = "error"
    return label, role_info, project_info


def get_yml_list(root_dir: str, task_num_threshold: int = -1):
    found_ymls = find_all_ymls(root_dir)
    all_files = []
    for yml_path in found_ymls:
        label, role_info, project_info = get_yml_label(yml_path, root_dir, task_num_threshold)
        if not role_info:
            role_info = {}
        if not project_info:
            project_info = {}
        if role_info:
            if role_info["path"] and not role_info["path"].startswith(root_dir):
                role_info["path"] = os.path.join(root_dir, role_info["path"])
            role_info["is_external_dependency"] = True if "." in role_info["name"] else False
        in_role = True if role_info else False
        in_project = True if project_info else False
        all_files.append(
            {
                "filepath": yml_path,
                "path_from_root": yml_path.replace(root_dir, "").lstrip("/"),
                "label": label,
                "role_info": role_info,
                "project_info": project_info,
                "in_role": in_role,
                "in_project": in_project,
            }
        )
    return all_files


def list_scan_target(root_dir: str, task_num_threshold: int = -1):
    yml_list = get_yml_list(root_dir=root_dir, task_num_threshold=task_num_threshold)
    known_roles = set()
    all_targets = []
    for yml_info in yml_list:
        if yml_info["label"] not in ["playbook", "taskfile"]:
            continue
        role_path = ""
        if yml_info["in_role"]:
            role_path = yml_info["role_info"].get("path", None)
        if role_path and role_path in known_roles:
            continue
        scan_type = ""
        filepath = ""
        path_from_root = ""
        if role_path:
            scan_type = "role"
            filepath = role_path
            path_from_root = role_path.replace(root_dir, "").lstrip("/")
            known_roles.add(role_path)
        else:
            scan_type = yml_info["label"]
            filepath = yml_info["filepath"]
            path_from_root = yml_info["path_from_root"]
        target_info = {
            "filepath": filepath,
            "path_from_root": path_from_root,
            "scan_type": scan_type,
        }
        all_targets.append(target_info)
    all_targets = sorted(all_targets, key=lambda x: x["filepath"])
    all_targets = sorted(all_targets, key=lambda x: x["scan_type"])
    return all_targets


def update_line_with_space(new_line_content, old_line_content, leading_spaces=0):
    """
    Returns the line of the input lines with mutation, having spaces
    exactly same as input yaml lines
    """
    new_line_content = new_line_content.lstrip(" ")
    if not leading_spaces:
        leading_spaces = len(old_line_content) - len(old_line_content.lstrip())
    return " " * leading_spaces + new_line_content


def populate_new_data_list(data, line_number_list):
    """
    Function to check diff in line between the
    first mutated results, and then copy the in
    between lines to mutated data lines
    """
    input_line_number = 0
    for each in line_number_list:
        input_line_number = int(each.lstrip("L").split("-")[0])
        break
    temp_data = data.splitlines(keepends=True)
    return temp_data[0 : input_line_number - 1]


def check_and_add_diff_lines(start_line, stop_line, lines, data_copy):
    """
    Function to check diff in line between the mutated results,
    and then copy the in between lines to mutated data lines
    """
    diff_in_line = stop_line - start_line
    data_copy.append("\n")
    for i in range(start_line, (start_line + diff_in_line) - 1):
        line = lines[i]
        data_copy.append(line)


def check_diff_and_copy_olddata_to_newdata(line_number_list, lines, new_data):
    """
    Function to find the old lines which weren't mutated by ARI rules,
    it need to be copied to new content as is
    """
    if line_number_list and isinstance(line_number_list, list):
        new_content_last_set = line_number_list[-1]
        new_content_last_line = int(new_content_last_set.lstrip("L").split("-")[1])
        if new_content_last_line < len(lines):
            for i in range(new_content_last_line, len(lines)):
                new_data.append(lines[i])
        return new_data


def update_and_append_new_line(new_line, old_line, leading_spaces, data_copy):
    """
    Function to get the leading space for the new ARI mutated line, with
    its equivaltent old line with space similar to the old line
    """
    line_with_adjusted_space = update_line_with_space(new_line, old_line, leading_spaces)
    data_copy.append(line_with_adjusted_space)
    return ""


def update_the_yaml_target(file_path, line_number_list, new_content_list):
    try:
        # Read the original YAML file
        with open(file_path, "r") as file:
            data = file.read()
        yaml = FormattedYAML(
            # Ansible only uses YAML 1.1, but others files should use newer 1.2 (ruamel.yaml defaults to 1.2)
        )
        data_copy = populate_new_data_list(data, line_number_list)
        stop_line_number = 0
        new_lines = []
        for iter in range(len(line_number_list)):
            line_number = line_number_list[iter]
            new_content = new_content_list[iter]
            input_line_number = line_number.lstrip("L").split("-")
            lines = data.splitlines(keepends=True)
            if new_lines:
                for i in range(len(new_lines)):
                    try:
                        data_copy.append(new_lines.pop(i))
                    except IndexError:
                        break
            new_lines = new_content.splitlines(keepends=True)
            # Update the specific line with new content
            start_line_number = int(input_line_number[0])
            if stop_line_number > 0 and (start_line_number - stop_line_number) > 1:
                check_and_add_diff_lines(stop_line_number, start_line_number, lines, data_copy)
            stop_line_number = int(input_line_number[1])
            diff_in_lines = stop_line_number - start_line_number
            temp_content = []
            start = start_line_number - 1
            end = stop_line_number - 1
            data_copy.append("\n")
            for i in range(start, end):
                line_number = i
                if len(lines) == i:
                    break
                try:
                    # always pop 1st element of the new lines list
                    new_line_content = new_lines.pop(0)
                except IndexError:
                    break
                if 0 <= line_number < len(lines):
                    # Preserve the original indentation
                    old_line_content = lines[line_number]
                    if "---" in old_line_content:
                        continue
                    if new_line_content in old_line_content:
                        leading_spaces = len(lines[line_number]) - len(lines[line_number].lstrip())
                        temp_content.append(new_line_content)
                        new_line_content = new_line_content.lstrip(" ")
                        lines[line_number] = " " * leading_spaces + new_line_content
                        data_copy.append(lines[line_number])
                    else:
                        new_line_key = new_line_content.split(":")
                        new_key = new_line_key[0].strip(" ")
                        for k in range(start, end):
                            if k < len(lines):
                                old_line_key = lines[k].split(":")
                                if "---" in old_line_key[0]:
                                    continue
                                old_key = old_line_key[0].strip(" ")
                                if "-" in old_line_key[0] and ":" not in lines[k] and "-" in new_key:
                                    # diff_in_lines = len(lines) - len(new_lines)
                                    leading_spaces = len(lines[k]) - len(lines[k].lstrip())
                                    if diff_in_lines > len(lines):
                                        for i in range(k, k + diff_in_lines):
                                            if lines[i] == "\n":
                                                lines.pop(i - 1)
                                                break
                                            elif i < len(lines) and ":" not in lines[i]:
                                                lines.pop(i)
                                            else:
                                                break
                                    new_line_content = update_and_append_new_line(new_line_content, lines[k], leading_spaces, data_copy)
                                    break
                                elif old_key == new_key:
                                    new_line_content = update_and_append_new_line(new_line_content, lines[k], 0, data_copy)
                                    break
                                elif old_key.rstrip("\n") == new_key:
                                    new_line_content = update_and_append_new_line(new_line_content, lines[k], 0, data_copy)
                                    break
                                elif old_key.rstrip("\n") in new_key.split("."):
                                    new_line_content = update_and_append_new_line(new_line_content, lines[k], 0, data_copy)
                                    break
                        if new_line_content:  # if there wasn't a match with old line, so this seems updated by ARI and added to w/o any change
                            data_copy.append(new_line_content)
                else:
                    return IndexError("Line number out of range.")
        # check for diff b/w new content and old contents,
        # and copy the old content that's not updated by ARI mutation
        data_copy = check_diff_and_copy_olddata_to_newdata(line_number_list, lines, data_copy)
        # Join the lines back to a single string
        updated_data = "".join(data_copy)
        # Parse the updated YAML content to ensure it is valid
        updated_parsed_data = yaml.load(updated_data)
        # Write the updated YAML content back to the file
        if updated_parsed_data:
            with open(file_path, "w") as file:
                yaml.dump(updated_parsed_data, file)
    except Exception as ex:
        logger.warning("YAML LINES: ARI fix update yaml by lines failed for file: '%s', with error: '%s'", file_path, ex)
