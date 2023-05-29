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

import datetime
import json
import os
import re
import yaml

try:
    # if `libyaml` is available, use C based loader for performance
    import _yaml  # noqa: F401
    from yaml import CSafeLoader as Loader
except Exception:
    # otherwise, use Python based loader
    from yaml import SafeLoader as Loader
from ansible.module_utils.parsing.convert_bool import boolean

import ansible_risk_insight.logger as logger
from .safe_glob import safe_glob
from .models import (
    ExecutableType,
    Inventory,
    InventoryType,
    LoadType,
    Play,
    Playbook,
    PlaybookFormatError,
    Repository,
    Role,
    Module,
    ModuleArgument,
    RoleInPlay,
    Task,
    TaskFile,
    TaskFormatError,
    Collection,
    BecomeInfo,
    ObjectList,
)
from .finder import (
    find_best_repo_root_path,
    find_collection_name_of_repo,
    find_module_name,
    get_task_blocks,
    search_inventory_files,
    find_module_dirs,
    search_module_files,
    search_taskfiles_for_playbooks,
    module_dir_patterns,
)
from .utils import (
    split_target_playbook_fullpath,
    split_target_taskfile_fullpath,
    get_module_specs_by_ansible_doc,
    get_documentation_in_module_file,
    get_class_by_arg_type,
    is_test_object,
)
from .awx_utils import could_be_playbook, could_be_taskfile

# collection info direcotry can be something like
#   "brightcomputing.bcm-9.1.11+41615.gitfab9053.info"
collection_info_dir_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+-[0-9]+\.[0-9]+\.[0-9]+.*\.info$")

string_module_options_re = re.compile(r"^([a-z0-9]+=(?:[^ ]*{{ [^ ]+ }}[^ ]*|[^ ])+\s?)+$")

loop_task_option_names = [
    "loop",
    "with_list",
    "with_items",
    "with_dict",
    # TODO: support the following
    "with_indexed_items",
    "with_flattened",
    "with_together",
    "with_sequence",
    "with_subelements",
    "with_nested",
    "with_cartesian",
    "with_random_choice",
]


def load_repository(
    path="",
    installed_collections_path="",
    installed_roles_path="",
    my_collection_name="",
    basedir="",
    target_playbook_path="",
    target_taskfile_path="",
    use_ansible_doc=True,
    skip_playbook_format_error=True,
    skip_task_format_error=True,
    include_test_contents=False,
    load_children=True,
):
    repoObj = Repository()

    repo_path = ""
    if path == "":
        # if path is empty, just load installed collections / roles
        repo_path = ""
    else:
        # otherwise, find the root path by searching playbooks
        try:
            repo_path = find_best_repo_root_path(path)
        except Exception:
            logger.debug('failed to find a root directory for ansible files; use "{}"' " but this may be wrong".format(path))
        if repo_path == "":
            repo_path = path

    if repo_path != "":
        if my_collection_name == "":
            my_collection_name = find_collection_name_of_repo(repo_path)
        if my_collection_name != "":
            repoObj.my_collection_name = my_collection_name

    if basedir == "":
        basedir = path

    logger.debug("start loading the repo {}".format(repo_path))
    logger.debug("start loading playbooks")
    repoObj.playbooks = load_playbooks(repo_path, basedir=basedir, include_test_contents=include_test_contents, load_children=load_children)
    logger.debug("done ... {} playbooks loaded".format(len(repoObj.playbooks)))
    logger.debug("start loading roles")
    repoObj.roles = load_roles(
        repo_path, basedir=basedir, use_ansible_doc=use_ansible_doc, include_test_contents=include_test_contents, load_children=load_children
    )
    logger.debug("done ... {} roles loaded".format(len(repoObj.roles)))
    logger.debug("start loading modules (that are defined in this repository)")
    repoObj.modules = load_modules(
        repo_path,
        basedir=basedir,
        collection_name=repoObj.my_collection_name,
        use_ansible_doc=use_ansible_doc,
        load_children=load_children,
    )
    logger.debug("done ... {} modules loaded".format(len(repoObj.modules)))
    logger.debug("start loading taskfiles (that are defined for playbooks in this" " repository)")
    repoObj.taskfiles = load_taskfiles(repo_path, basedir=basedir, load_children=load_children)
    logger.debug("done ... {} task files loaded".format(len(repoObj.taskfiles)))
    logger.debug("start loading inventory files")
    repoObj.inventories = load_inventories(repo_path, basedir=basedir)
    logger.debug("done ... {} inventory files loaded".format(len(repoObj.inventories)))
    logger.debug("start loading installed collections")
    repoObj.installed_collections = load_installed_collections(installed_collections_path)

    logger.debug("done ... {} collections loaded".format(len(repoObj.installed_collections)))
    logger.debug("start loading installed roles")
    repoObj.installed_roles = load_installed_roles(installed_roles_path)
    logger.debug("done ... {} roles loaded".format(len(repoObj.installed_roles)))
    repoObj.requirements = load_requirements(path=repo_path)
    name = os.path.basename(path)
    repoObj.name = name
    _path = name
    if os.path.abspath(repo_path).startswith(os.path.abspath(path)):
        relative = os.path.abspath(repo_path)[len(os.path.abspath(path)) :]
        _path = os.path.join(name, relative)
    repoObj.path = _path
    repoObj.installed_collections_path = installed_collections_path
    repoObj.installed_roles_path = installed_roles_path
    repoObj.target_playbook_path = target_playbook_path
    repoObj.target_taskfile_path = target_taskfile_path
    logger.debug("done")

    return repoObj


def load_installed_collections(installed_collections_path):
    search_path = installed_collections_path
    if installed_collections_path == "" or not os.path.exists(search_path):
        return []
    if os.path.exists(os.path.join(search_path, "ansible_collections")):
        search_path = os.path.join(search_path, "ansible_collections")
    dirs = os.listdir(search_path)
    basedir = os.path.dirname(os.path.normpath(installed_collections_path))
    collections = []
    for d in dirs:
        if collection_info_dir_re.match(d):
            continue
        if not os.path.exists(os.path.join(search_path, d)):
            continue
        subdirs = os.listdir(os.path.join(search_path, d))
        for sd in subdirs:
            collection_path = os.path.join(search_path, d, sd)
            try:
                c = load_collection(collection_dir=collection_path, basedir=basedir)
                collections.append(c)
            except Exception:
                logger.exception("error while loading the collection at {}".format(collection_path))
    return collections


def load_inventory(path, basedir=""):
    invObj = Inventory()
    fullpath = ""
    if os.path.exists(path) and path != "" and path != ".":
        fullpath = path
    if os.path.exists(os.path.join(basedir, path)):
        fullpath = os.path.normpath(os.path.join(basedir, path))
    if fullpath == "":
        raise ValueError("file not found")
    defined_in = fullpath
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    invObj.defined_in = defined_in
    base_parts = os.path.splitext(os.path.basename(fullpath))
    invObj.name = base_parts[0]
    file_ext = base_parts[1]
    dirname = os.path.dirname(fullpath)
    inventory_type = InventoryType.UNKNOWN_TYPE
    group_name = ""
    host_name = ""
    if dirname.endswith("/group_vars"):
        inventory_type = InventoryType.GROUP_VARS_TYPE
        group_name = base_parts[0]
    elif dirname.endswith("/host_vars"):
        inventory_type = InventoryType.HOST_VARS_TYPE
        host_name = base_parts[0]
    invObj.inventory_type = inventory_type
    invObj.group_name = group_name
    invObj.host_name = host_name
    data = {}
    if file_ext == "":
        # TODO: parse it as INI file
        pass
    elif file_ext == ".yml" or file_ext == ".yaml":
        with open(fullpath, "r") as file:
            try:
                data = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load this yaml file (inventory); {}".format(e.args[0]))
    elif file_ext == ".json":
        with open(fullpath, "r") as file:
            try:
                data = json.load(file)
            except Exception as e:
                logger.debug("failed to load this json file (inventory); {}".format(e.args[0]))
    invObj.variables = data
    return invObj


def load_inventories(path, basedir=""):

    if not os.path.exists(path):
        return []
    inventories = []
    inventory_file_paths = search_inventory_files(path)
    if len(inventory_file_paths) > 0:
        for inventory_path in inventory_file_paths:
            try:
                iv = load_inventory(inventory_path, basedir=basedir)
                inventories.append(iv)
            except Exception:
                logger.exception("error while loading the inventory file at {}".format(inventory_path))
    return inventories


def load_play(
    path,
    index,
    play_block_dict,
    role_name="",
    collection_name="",
    parent_key="",
    parent_local_key="",
    yaml_lines="",
    basedir="",
    skip_task_format_error=True,
):
    pbObj = Play()
    if play_block_dict is None:
        raise ValueError("play block dict is required to load Play")
    if not isinstance(play_block_dict, dict):
        raise PlaybookFormatError("this play block is not loaded as dict; maybe this is not a" " playbook")
    data_block = play_block_dict
    if "hosts" not in data_block and "import_playbook" not in data_block and "include" not in data_block:
        raise PlaybookFormatError('this play block does not have "hosts", "import_playbook" and' ' "include"; maybe this is not a playbook')

    pbObj.index = index
    pbObj.role = role_name
    pbObj.collection = collection_name
    pbObj.set_key(parent_key, parent_local_key)
    play_name = data_block.get("name", "")
    collections_in_play = data_block.get("collections", [])
    pre_tasks = []
    post_tasks = []
    tasks = []
    roles = []
    variables = {}
    module_defaults = {}
    play_options = {}
    import_module = ""
    import_playbook = ""

    tasks_keys = ["pre_tasks", "tasks", "post_tasks"]
    keys = [k for k in data_block if k not in tasks_keys]
    keys.extend(tasks_keys)
    task_count = 0

    for k in keys:
        if k not in data_block:
            continue
        v = data_block[k]
        if k == "name":
            pass
        elif k == "collections":
            pass
        elif k == "pre_tasks":
            if not isinstance(v, list):
                continue
            task_blocks, _ = get_task_blocks(task_dict_list=v)
            if task_blocks is None:
                continue
            for task_dict in task_blocks:
                i = task_count
                try:
                    t = load_task(
                        path=path,
                        index=i,
                        task_block_dict=task_dict,
                        role_name=role_name,
                        collection_name=collection_name,
                        collections_in_play=collections_in_play,
                        play_index=index,
                        parent_key=pbObj.key,
                        parent_local_key=pbObj.local_key,
                        yaml_lines=yaml_lines,
                        basedir=basedir,
                    )
                    pre_tasks.append(t)
                except TaskFormatError:
                    if skip_task_format_error:
                        logger.debug("this task is wrong format; skip the task in {}," " index: {}; skip this".format(path, i))
                    else:
                        raise TaskFormatError(f"this task is wrong format; skip the task in {path}," " index: {i}")
                except Exception:
                    logger.exception("error while loading the task at {} (index={})".format(path, i))
                finally:
                    task_count += 1
        elif k == "tasks":
            if not isinstance(v, list):
                continue
            task_blocks, _ = get_task_blocks(task_dict_list=v)
            if task_blocks is None:
                continue
            for task_dict in task_blocks:
                i = task_count
                try:
                    t = load_task(
                        path=path,
                        index=i,
                        task_block_dict=task_dict,
                        role_name=role_name,
                        collection_name=collection_name,
                        collections_in_play=collections_in_play,
                        play_index=index,
                        parent_key=pbObj.key,
                        parent_local_key=pbObj.local_key,
                        yaml_lines=yaml_lines,
                        basedir=basedir,
                    )
                    tasks.append(t)
                except TaskFormatError:
                    if skip_task_format_error:
                        logger.debug("this task is wrong format; skip the task in {}," " index: {}; skip this".format(path, i))
                    else:
                        raise TaskFormatError(f"this task is wrong format; skip the task in {path}," " index: {i}")
                except Exception:
                    logger.exception("error while loading the task at {} (index={})".format(path, i))
                finally:
                    task_count += 1
        elif k == "post_tasks":
            if not isinstance(v, list):
                continue
            task_blocks, _ = get_task_blocks(task_dict_list=v)
            if task_blocks is None:
                continue
            for task_dict in task_blocks:
                i = task_count
                try:
                    t = load_task(
                        path=path,
                        index=i,
                        task_block_dict=task_dict,
                        role_name=role_name,
                        collection_name=collection_name,
                        collections_in_play=collections_in_play,
                        play_index=index,
                        parent_key=pbObj.key,
                        parent_local_key=pbObj.local_key,
                        yaml_lines=yaml_lines,
                        basedir=basedir,
                    )
                    post_tasks.append(t)
                except TaskFormatError:
                    if skip_task_format_error:
                        logger.debug("this task is wrong format; skip the task in {}," " index: {}; skip this".format(path, i))
                    else:
                        raise TaskFormatError(f"this task is wrong format; skip the task in {path}," " index: {i}")
                except Exception:
                    logger.exception("error while loading the task at {} (index={})".format(path, i))
                finally:
                    task_count += 1
        elif k == "roles":
            if not isinstance(v, list):
                continue
            for i, r_block in enumerate(v):
                r_name = ""
                role_options = {}
                if isinstance(r_block, dict):
                    r_name = r_block.get("role", "")
                    role_options = {}
                    for k, v in r_block.items():
                        role_options[k] = v
                elif isinstance(r_block, str):
                    r_name = r_block
                try:
                    rip = load_roleinplay(
                        name=r_name,
                        options=role_options,
                        defined_in=path,
                        role_index=i,
                        play_index=index,
                        role_name=role_name,
                        collection_name=collection_name,
                        collections_in_play=collections_in_play,
                        basedir=basedir,
                    )
                    roles.append(rip)
                except Exception:
                    logger.exception("error while loading the role in playbook at {}" " (play_index={}, role_index={})".format(path, pbObj.index, i))
        elif k == "vars":
            if not isinstance(v, dict):
                continue
            variables = v
        elif k == "module_defaults":
            if not isinstance(v, dict):
                continue
            module_defaults = v
        elif k == "import_playbook":
            if not isinstance(v, str):
                continue
            import_module = k
            import_playbook = v
        elif k == "include":
            if not isinstance(v, str):
                continue
            import_module = k
            import_playbook = v
        else:
            play_options.update({k: v})

    pbObj.name = play_name
    pbObj.defined_in = path
    pbObj.import_module = import_module
    pbObj.import_playbook = import_playbook
    pbObj.pre_tasks = pre_tasks
    pbObj.tasks = tasks
    pbObj.post_tasks = post_tasks
    pbObj.roles = roles
    pbObj.variables = variables
    pbObj.module_defaults = module_defaults
    pbObj.options = play_options
    pbObj.become = BecomeInfo.from_options(play_options)
    pbObj.collections_in_play = collections_in_play

    return pbObj


def load_roleinplay(
    name,
    options,
    defined_in,
    role_index,
    play_index,
    role_name="",
    collection_name="",
    collections_in_play=[],
    playbook_yaml="",
    basedir="",
):
    ripObj = RoleInPlay()
    if name == "":
        if "name" in options:
            name = options["name"]
            options.pop("name", None)
    ripObj.name = name
    ripObj.options = options
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    ripObj.defined_in = defined_in
    ripObj.role = role_name
    ripObj.collection = collection_name
    ripObj.role_index = role_index
    ripObj.play_index = play_index
    ripObj.collections_in_play = collections_in_play

    return ripObj


def load_playbook(path="", yaml_str="", role_name="", collection_name="", basedir="", skip_playbook_format_error=True, skip_task_format_error=True):
    pbObj = Playbook()
    fullpath = ""
    if yaml_str:
        fullpath = path
    else:
        if os.path.exists(path) and path != "" and path != ".":
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.normpath(os.path.join(basedir, path))
        if fullpath == "":
            raise ValueError("file not found")
    defined_in = fullpath
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    pbObj.defined_in = defined_in
    pbObj.name = os.path.basename(fullpath)
    pbObj.role = role_name
    pbObj.collection = collection_name
    pbObj.set_key()
    yaml_lines = ""
    data = None
    if yaml_str:
        try:
            yaml_lines = yaml_str
            data = yaml.load(yaml_lines, Loader=Loader)
        except Exception as e:
            if skip_playbook_format_error:
                logger.debug(f"failed to load this yaml string to load playbook, skip this yaml; {e}")
            else:
                raise PlaybookFormatError(f"failed to load this yaml string to load playbook; {e}")
    elif fullpath != "":
        with open(fullpath, "r") as file:
            try:
                yaml_lines = file.read()
                data = yaml.load(yaml_lines, Loader=Loader)
            except Exception as e:
                if skip_playbook_format_error:
                    logger.debug(f"failed to load this yaml file to load playbook, skip this yaml; {e}")
                else:
                    raise PlaybookFormatError(f"failed to load this yaml file to load playbook; {e}")
    if data is None:
        return pbObj
    if not isinstance(data, list):
        raise PlaybookFormatError("playbook must be loaded as a list, but got {}".format(type(data).__name__))

    if yaml_lines:
        pbObj.yaml_lines = yaml_lines

    plays = []
    for i, play_dict in enumerate(data):
        try:
            play = load_play(
                path=defined_in,
                index=i,
                play_block_dict=play_dict,
                role_name=role_name,
                collection_name=collection_name,
                parent_key=pbObj.key,
                parent_local_key=pbObj.local_key,
                yaml_lines=yaml_str,
                basedir=basedir,
                skip_task_format_error=skip_task_format_error,
            )
            plays.append(play)
        except PlaybookFormatError:
            if skip_playbook_format_error:
                logger.debug("this play is wrong format; skip the play in {}, index: {}, skip this play".format(fullpath, i))
            else:
                raise PlaybookFormatError(f"this play is wrong format; skip the play in {fullpath}, index: {i}")
        except Exception:
            logger.exception("error while loading the play at {} (index={})".format(fullpath, i))
    pbObj.plays = plays

    return pbObj


def load_playbooks(path, basedir="", skip_playbook_format_error=True, skip_task_format_error=True, include_test_contents=False, load_children=True):
    if path == "":
        return []
    patterns = [
        os.path.join(path, "/*.ya?ml"),
        os.path.join(path, "/playbooks/**/*.ya?ml"),
    ]
    if include_test_contents:
        patterns.append(os.path.join(path, "tests/**/*.ya?ml"))
        patterns.append(os.path.join(path, "molecule/**/*.ya?ml"))
    candidates = safe_glob(patterns, recursive=True)
    playbooks = []
    playbook_names = []
    for fpath in candidates:
        if could_be_playbook(fpath):
            relative_path = ""
            if fpath.startswith(path):
                relative_path = fpath[len(path) :]
            if "/roles/" in relative_path:
                continue
            p = None
            try:
                p = load_playbook(
                    path=fpath,
                    basedir=basedir,
                    skip_playbook_format_error=skip_playbook_format_error,
                    skip_task_format_error=skip_task_format_error,
                )
            except PlaybookFormatError as e:
                if skip_playbook_format_error:
                    logger.debug("this file is not in a playbook format, maybe not a playbook file, skip this: {}".format(e.args[0]))
                    continue
                else:
                    raise PlaybookFormatError(f"this file is not in a playbook format, maybe not a playbook file: {e.args[0]}")
            except Exception:
                logger.exception("error while loading the playbook at {}".format(fpath))
            if p:
                if load_children:
                    playbooks.append(p)
                    playbook_names.append(p.defined_in)
                else:
                    playbooks.append(p.defined_in)
                    playbook_names.append(p.defined_in)
    if not load_children:
        playbooks = sorted(playbooks)
    return playbooks


def load_role(
    path,
    name="",
    collection_name="",
    module_dir_paths=[],
    basedir="",
    use_ansible_doc=True,
    skip_playbook_format_error=True,
    skip_task_format_error=True,
    include_test_contents=False,
    load_children=True,
):
    roleObj = Role()
    fullpath = ""
    if os.path.exists(path) and path != "" and path != ".":
        fullpath = path
    if os.path.exists(os.path.join(basedir, path)):
        fullpath = os.path.normpath(os.path.join(basedir, path))
    if fullpath == "":
        raise ValueError(f"directory not found: {path}, {basedir}")
    else:
        # some roles can be found at "/path/to/role.name/role.name"
        # especially when the role has dependency roles
        # so we try it here
        basename = os.path.basename(fullpath)
        tmp_fullpath = os.path.join(fullpath, basename)
        if os.path.exists(tmp_fullpath):
            fullpath = tmp_fullpath
    meta_file_path = ""
    defaults_dir_path = ""
    vars_dir_path = ""
    tasks_dir_path = ""
    handlers_dir_path = ""
    includes_dir_path = ""
    if fullpath != "":
        meta_file_path = os.path.join(fullpath, "meta/main.yml")
        defaults_dir_path = os.path.join(fullpath, "defaults")
        vars_dir_path = os.path.join(fullpath, "vars")
        tasks_dir_path = os.path.join(fullpath, "tasks")
        tests_dir_path = os.path.join(fullpath, "tests")
        handlers_dir_path = os.path.join(fullpath, "handlers")
        includes_dir_path = os.path.join(fullpath, "includes")
    if os.path.exists(meta_file_path):
        with open(meta_file_path, "r") as file:
            try:
                roleObj.metadata = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load this yaml file to raed metadata; {}".format(e.args[0]))

            if roleObj.metadata is not None and isinstance(roleObj.metadata, dict):
                roleObj.dependency["roles"] = roleObj.metadata.get("dependencies", [])
                roleObj.dependency["collections"] = roleObj.metadata.get("collections", [])

    requirements_yml_path = os.path.join(fullpath, "requirements.yml")
    if os.path.exists(requirements_yml_path):
        with open(requirements_yml_path, "r") as file:
            try:
                roleObj.requirements = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load requirements.yml; {}".format(e.args[0]))

    parts = tasks_dir_path.split("/")
    if len(parts) < 2:
        raise ValueError("role path is wrong")
    role_name = parts[-2] if name == "" else name
    roleObj.name = role_name
    defined_in = fullpath
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    roleObj.defined_in = defined_in
    is_test = is_test_object(defined_in)

    collection = ""
    fqcn = role_name
    if collection_name != "" and not is_test:
        collection = collection_name
        fqcn = "{}.{}".format(collection_name, role_name)
    roleObj.collection = collection
    roleObj.fqcn = fqcn
    roleObj.set_key()

    playbooks = load_playbooks(
        path=fullpath,
        basedir=basedir,
        skip_playbook_format_error=skip_playbook_format_error,
        skip_task_format_error=skip_task_format_error,
        include_test_contents=include_test_contents,
        load_children=load_children,
    )
    roleObj.playbooks = playbooks

    if os.path.exists(defaults_dir_path):
        patterns = [
            defaults_dir_path + "/**/*.ya?ml",
        ]
        defaults_yaml_files = safe_glob(patterns, recursive=True)
        default_variables = {}
        for fpath in defaults_yaml_files:
            with open(fpath, "r") as file:
                try:
                    vars_in_yaml = yaml.load(file, Loader=Loader)
                    if vars_in_yaml is None:
                        continue
                    if not isinstance(vars_in_yaml, dict):
                        continue
                    default_variables.update(vars_in_yaml)
                except Exception as e:
                    logger.debug("failed to load this yaml file to read default" " variables; {}".format(e.args[0]))
        roleObj.default_variables = default_variables

    if os.path.exists(vars_dir_path):
        patterns = [vars_dir_path + "/**/*.ya?ml"]
        vars_yaml_files = safe_glob(patterns, recursive=True)
        variables = {}
        for fpath in vars_yaml_files:
            with open(fpath, "r") as file:
                try:
                    vars_in_yaml = yaml.load(file, Loader=Loader)
                    if vars_in_yaml is None:
                        continue
                    if not isinstance(vars_in_yaml, dict):
                        continue
                    variables.update(vars_in_yaml)
                except Exception as e:
                    logger.debug("failed to load this yaml file to read variables; {}".format(e.args[0]))
        roleObj.variables = variables

    modules = []
    module_files = search_module_files(fullpath, module_dir_paths)

    if not load_children:
        use_ansible_doc = False

    module_specs = {}
    if use_ansible_doc:
        module_specs = get_module_specs_by_ansible_doc(
            module_files=module_files,
            fqcn_prefix=collection_name,
            search_path=fullpath,
        )

    for module_file_path in module_files:
        m = None
        try:
            m = load_module(
                module_file_path,
                collection_name=collection_name,
                role_name=fqcn,
                basedir=basedir,
                use_ansible_doc=use_ansible_doc,
                module_specs=module_specs,
            )
        except Exception:
            logger.exception("error while loading the module at {}".format(module_file_path))
        if load_children:
            modules.append(m)
        else:
            modules.append(m.defined_in)
    if not load_children:
        modules = sorted(modules)
    roleObj.modules = modules

    patterns = [tasks_dir_path + "/**/*.ya?ml"]
    # ansible.network collection has this type of another taskfile directory
    if os.path.exists(includes_dir_path):
        patterns.extend([includes_dir_path + "/**/*.ya?ml"])
    if include_test_contents:
        patterns.extend([tests_dir_path + "/**/*.ya?ml"])
    task_yaml_files = safe_glob(patterns, recursive=True)

    taskfiles = []
    for task_yaml_path in task_yaml_files:
        tf = None
        if not could_be_taskfile(task_yaml_path):
            continue
        try:
            tf = load_taskfile(
                task_yaml_path,
                role_name=fqcn,
                collection_name=collection_name,
                basedir=basedir,
                skip_task_format_error=skip_task_format_error,
            )
        except TaskFormatError as e:
            if skip_task_format_error:
                logger.debug(f"Task format error found; skip this taskfile {task_yaml_path}")
            else:
                raise TaskFormatError(f"Task format error found: {e.args[0]}")
        except Exception:
            logger.exception("error while loading the task file at {}".format(task_yaml_path))
        if not tf:
            continue
        if load_children:
            taskfiles.append(tf)
        else:
            taskfiles.append(tf.defined_in)
    if not load_children:
        taskfiles = sorted(taskfiles)
    roleObj.taskfiles = taskfiles

    if os.path.exists(handlers_dir_path):
        handler_patterns = [handlers_dir_path + "/**/*.ya?ml"]
        handler_files = safe_glob(handler_patterns, recursive=True)

        handlers = []
        for handler_yaml_path in handler_files:
            tf = None
            try:
                tf = load_taskfile(
                    handler_yaml_path,
                    role_name=fqcn,
                    collection_name=collection_name,
                    basedir=basedir,
                    skip_task_format_error=skip_task_format_error,
                )
            except TaskFormatError as e:
                if skip_task_format_error:
                    logger.debug(f"Task format error found; skip this taskfile {task_yaml_path}")
                else:
                    raise TaskFormatError(f"Task format error found: {e.args[0]}")
            except Exception:
                logger.exception("error while loading the task file at {}".format(task_yaml_path))
            if not tf:
                continue
            if load_children:
                handlers.append(tf)
            else:
                handlers.append(tf.defined_in)
        if not load_children:
            handlers = sorted(handlers)
        roleObj.handlers = handlers

    return roleObj


def load_roles(
    path,
    basedir="",
    use_ansible_doc=True,
    skip_playbook_format_error=True,
    skip_task_format_error=True,
    include_test_contents=False,
    load_children=True,
):

    if path == "":
        return []
    roles_patterns = ["roles", "playbooks/roles", "playbook/roles"]
    roles_dir_path = ""
    for r_p in roles_patterns:
        candidate = os.path.join(path, r_p)
        if os.path.exists(candidate):
            roles_dir_path = candidate
            break

    role_dirs = []
    if roles_dir_path:
        dirs = os.listdir(roles_dir_path)
        role_dirs = [os.path.join(roles_dir_path, dir_name) for dir_name in dirs]

    if include_test_contents:
        test_targets_dir = os.path.join(path, "tests/integration/targets")
        if os.path.exists(test_targets_dir):
            test_names = os.listdir(test_targets_dir)
            for test_name in test_names:
                test_dir = os.path.join(test_targets_dir, test_name)
                test_tasks_dir = os.path.join(test_dir, "tasks")
                test_sub_roles_dir = os.path.join(test_dir, "roles")
                if os.path.exists(test_tasks_dir):
                    role_dirs.append(test_dir)
                elif os.path.exists(test_sub_roles_dir):
                    test_sub_role_names = os.listdir(test_sub_roles_dir)
                    for test_sub_role_name in test_sub_role_names:
                        test_sub_role_dir = os.path.join(test_sub_roles_dir, test_sub_role_name)
                        role_dirs.append(test_sub_role_dir)

    if not role_dirs:
        return []

    roles = []
    for role_dir in role_dirs:
        try:
            r = load_role(
                path=role_dir,
                basedir=basedir,
                use_ansible_doc=use_ansible_doc,
                skip_playbook_format_error=skip_playbook_format_error,
                skip_task_format_error=skip_task_format_error,
                include_test_contents=include_test_contents,
            )
        except Exception:
            logger.exception("error while loading the role at {}".format(role_dir))
        if load_children:
            roles.append(r)
        else:
            roles.append(r.defined_in)
    if not load_children:
        roles = sorted(roles)
    return roles


def load_requirements(path):
    requirements = {}
    requirements_yml_path = os.path.join(path, "requirements.yml")
    if os.path.exists(requirements_yml_path):
        with open(requirements_yml_path, "r") as file:
            try:
                requirements = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load requirements.yml; {}".format(e.args[0]))
    return requirements


def load_installed_roles(installed_roles_path):
    search_path = installed_roles_path
    if installed_roles_path == "" or not os.path.exists(search_path):
        return []
    dirs = os.listdir(search_path)
    roles = []
    basedir = os.path.dirname(os.path.normpath(installed_roles_path))
    for d in dirs:
        role_path = os.path.join(installed_roles_path, d)
        role_meta_files = safe_glob(role_path + "/**/meta/main.ya?ml", recursive=True)

        roles_root_dirs = set([f.split("/roles/")[-2] for f in role_meta_files if "/roles/" in f])
        module_dirs = []
        for role_root_dir in roles_root_dirs:
            moddirs = find_module_dirs(role_root_dir)
            module_dirs.extend(moddirs)

        for i, role_meta_file in enumerate(role_meta_files):
            role_dir_path = role_meta_file.replace("/meta/main.yml", "").replace("/meta/main.yaml", "")
            module_dir_paths = []
            if i == 0:
                module_dir_paths = module_dirs
            try:
                r = load_role(
                    role_dir_path,
                    module_dir_paths=module_dir_paths,
                    basedir=basedir,
                )
                roles.append(r)
            except Exception:
                logger.exception("error while loading the role at {}".format(role_dir_path))
    return roles


def load_module(module_file_path, collection_name="", role_name="", basedir="", use_ansible_doc=True, module_specs={}):
    moduleObj = Module()
    if module_file_path == "":
        raise ValueError("require module file path to load a Module")
    fullpath = ""
    if os.path.exists(module_file_path) and module_file_path != "" and module_file_path != ".":
        fullpath = module_file_path
    if os.path.exists(os.path.join(basedir, module_file_path)):
        fullpath = os.path.normpath(os.path.join(basedir, module_file_path))
    if fullpath == "":
        raise ValueError(f"module file not found: {module_file_path}, {basedir}")

    file_name = os.path.basename(module_file_path)
    module_name = file_name.replace(".py", "")

    # some collections have modules like `plugins/modules/xxxx/yyyy.py`
    # so try finding `xxxx` part by checking module file path
    for dir_pattern in module_dir_patterns:
        separator = dir_pattern + "/"
        if separator in module_file_path:
            module_name = module_file_path.split(separator)[-1].replace(".py", "").replace("/", ".")
            break

    moduleObj.name = module_name
    if collection_name != "":
        moduleObj.collection = collection_name
        moduleObj.fqcn = "{}.{}".format(collection_name, module_name)
    elif role_name != "":
        # if module is defined in a role, it does not have real fqcn
        moduleObj.role = role_name
        moduleObj.fqcn = module_name
    defined_in = module_file_path
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    moduleObj.defined_in = defined_in

    arguments = []
    doc_yaml = ""
    examples = ""
    if use_ansible_doc:
        # running `ansible-doc` for each module causes speed problem due to overhead,
        # so use it for all modules and pick up the doc for the module here
        if module_specs:
            doc_yaml = module_specs.get(moduleObj.fqcn, {}).get("doc", "")
            examples = module_specs.get(moduleObj.fqcn, {}).get("examples", "")
    else:
        # parse the script file for a quick scan (this does not contain doc from `doc_fragments`)
        doc_yaml = get_documentation_in_module_file(fullpath)
    if doc_yaml:
        doc_dict = {}
        try:
            doc_dict = yaml.load(doc_yaml, Loader=Loader)
        except Exception:
            logger.debug(f"failed to load the arguments documentation of the module: {module_name}")
        if not doc_dict:
            doc_dict = {}
        arg_specs = doc_dict.get("options", {})
        if isinstance(arg_specs, dict):
            for arg_name in arg_specs:
                arg_spec = arg_specs[arg_name]
                if not isinstance(arg_spec, dict):
                    continue
                arg_value_type = get_class_by_arg_type(arg_spec.get("type", None))
                arg_value_type_str = ""
                if arg_value_type:
                    arg_value_type_str = arg_value_type.__name__

                arg_elements_type = get_class_by_arg_type(arg_spec.get("elements", None))
                arg_elements_type_str = ""
                if arg_elements_type:
                    arg_elements_type_str = arg_elements_type.__name__
                required = None
                try:
                    required = boolean(arg_spec.get("required", "false"))
                except Exception:
                    pass
                arg = ModuleArgument(
                    name=arg_name,
                    type=arg_value_type_str,
                    elements=arg_elements_type_str,
                    required=required,
                    description=arg_spec.get("description", ""),
                    default=arg_spec.get("default", None),
                    choices=arg_spec.get("choices", None),
                    aliases=arg_spec.get("aliases", None),
                )
                arguments.append(arg)
    moduleObj.documentation = doc_yaml
    moduleObj.examples = examples
    moduleObj.arguments = arguments

    moduleObj.set_key()

    return moduleObj


builtin_modules_file_name = "ansible_builtin_modules.json"
builtin_modules = {}


def load_builtin_modules():
    global builtin_modules
    if builtin_modules:
        return builtin_modules
    base_path = os.path.dirname(__file__)
    data_path = os.path.join(base_path, builtin_modules_file_name)
    module_list = ObjectList.from_json(fpath=data_path)
    builtin_modules = {m.name: m for m in module_list.items}
    return builtin_modules


# modules in a SCM repo should be in `library` dir in the best practice case
# https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html
# however, it is often defined in `plugins/modules` directory,
# so we search both the directories
def load_modules(path, basedir="", collection_name="", module_dir_paths=[], use_ansible_doc=True, load_children=True):
    if path == "":
        return []
    if not os.path.exists(path):
        return []
    module_files = search_module_files(path, module_dir_paths)

    if len(module_files) == 0:
        return []

    if not load_children:
        use_ansible_doc = False

    module_specs = {}
    if use_ansible_doc:
        module_specs = get_module_specs_by_ansible_doc(
            module_files=module_files,
            fqcn_prefix=collection_name,
            search_path=path,
        )

    modules = []
    for module_file_path in module_files:
        m = None
        try:
            m = load_module(
                module_file_path,
                collection_name=collection_name,
                basedir=basedir,
                use_ansible_doc=use_ansible_doc,
                module_specs=module_specs,
            )
        except Exception:
            logger.exception("error while loading the module at {}".format(module_file_path))
        if load_children:
            modules.append(m)
        else:
            modules.append(m.defined_in)
    if not load_children:
        modules = sorted(modules)
    return modules


def load_task(
    path,
    index,
    task_block_dict,
    role_name="",
    collection_name="",
    collections_in_play=[],
    play_index=-1,
    parent_key="",
    parent_local_key="",
    yaml_lines="",
    basedir="",
):

    taskObj = Task()
    fullpath = ""
    if yaml_lines:
        fullpath = path
    else:
        if os.path.exists(path) and path != "" and path != ".":
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.normpath(os.path.join(basedir, path))
        if fullpath == "":
            raise ValueError("file not found")
        if not fullpath.endswith(".yml") and not fullpath.endswith(".yaml"):
            raise ValueError('task yaml file must be ".yml" or ".yaml"')
    if task_block_dict is None:
        raise ValueError("task block dict is required to load Task")
    if not isinstance(task_block_dict, dict):
        raise TaskFormatError(f"this task block is not a dict, but {type(task_block_dict).__name__}; maybe this is not a task")
    data_block = task_block_dict
    task_name = ""
    module_name = find_module_name(task_block_dict)
    module_short_name = module_name.split(".")[-1]
    task_options = {}
    module_options = {}
    for k, v in data_block.items():
        if k == "name":
            task_name = v
        if k == module_name:
            module_options = v
        else:
            task_options.update({k: v})

    taskObj.set_yaml_lines(fullpath=fullpath, yaml_lines=yaml_lines, task_name=task_name, module_name=module_name, module_options=module_options)

    # module_options can be passed as a string like below
    #
    # - name: sample of string module options
    #   ufw: port={{ item }} proto=tcp rule=allow
    #   with_items:
    #   - 5222
    #   - 5269
    if isinstance(module_options, str):
        if string_module_options_re.match(module_options):
            new_module_options = {}
            unknown_key = "__unknown_option_name__"
            if module_short_name in ["import_role", "include_role"]:
                unknown_key = "name"
            elif module_short_name in [
                "import_tasks",
                "include_tasks",
                "include",
            ]:
                unknown_key = "file"
            matched_options = string_module_options_re.findall(module_options)
            if len(matched_options) == 0:
                new_module_options[unknown_key] = module_options
            else:
                unknown_key_val = module_options.split(matched_options[0])[0]
                if unknown_key_val != "":
                    new_module_options[unknown_key] = unknown_key_val
                for p in matched_options:
                    key = p.split("=")[0]
                    val = "=".join(p.split("=")[1:])
                    new_module_options[key] = val
            module_options = new_module_options
    executable = module_name
    executable_type = ExecutableType.MODULE_TYPE
    if module_short_name in ["import_role", "include_role"]:
        role_ref = ""
        if isinstance(module_options, str):
            role_ref = module_options
        elif isinstance(module_options, dict):
            role_ref = module_options.get("name", "")
        executable = role_ref
        executable_type = ExecutableType.ROLE_TYPE
    if module_short_name in ["import_tasks", "include_tasks", "include"]:
        taskfile_ref = ""
        if isinstance(module_options, str):
            taskfile_ref = module_options
        elif isinstance(module_options, dict):
            taskfile_ref = module_options.get("file", "")
        executable = taskfile_ref
        executable_type = ExecutableType.TASKFILE_TYPE

    taskObj.name = task_name
    taskObj.role = role_name
    taskObj.collection = collection_name
    defined_in = fullpath
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    taskObj.defined_in = defined_in
    taskObj.index = index
    taskObj.play_index = play_index
    taskObj.executable = executable
    taskObj.executable_type = executable_type
    taskObj.collections_in_play = collections_in_play
    taskObj.set_key(parent_key, parent_local_key)

    variables = {}
    # get variables for this task
    if "vars" in task_options:
        vars_in_task = task_options.get("vars", {})
        if vars_in_task is not None and isinstance(vars_in_task, dict):
            variables.update(vars_in_task)

    module_defaults = {}
    # get module_defaults in the task
    # NOTE: if module_defaults is defined in the parent block, get_task_blocks()
    #       automatically embed it to the task's module_defaults)
    if "module_defaults" in task_options:
        m_default_in_task = task_options.get("module_defaults", {})
        if m_default_in_task and isinstance(m_default_in_task, dict):
            module_defaults.update(m_default_in_task)

    set_facts = {}
    # if the Task is set_fact, set variables too
    if module_short_name == "set_fact":
        if isinstance(module_options, dict):
            set_facts.update(module_options)

    registered_variables = {}
    # set variables if this task register a new var
    if "register" in task_options:
        register_var_name = task_options.get("register", "")
        if register_var_name is not None and isinstance(register_var_name, str) and register_var_name != "":
            registered_variables.update({register_var_name: taskObj.key})

    # set loop variables when loop / with_xxxx are there
    loop_info = {}
    for k in task_options:
        if k in loop_task_option_names:
            loop_var = task_options.get("loop_control", {}).get("loop_var", "item")
            loop_info[loop_var] = task_options.get(k, [])

    taskObj.options = task_options
    taskObj.become = BecomeInfo.from_options(task_options)
    taskObj.variables = variables
    taskObj.module_defaults = module_defaults
    taskObj.registered_variables = registered_variables
    taskObj.set_facts = set_facts
    taskObj.loop = loop_info
    taskObj.module = module_name
    taskObj.module_options = module_options

    return taskObj


def load_taskfile(path, yaml_str="", role_name="", collection_name="", basedir="", skip_task_format_error=True):
    tfObj = TaskFile()
    fullpath = ""
    if yaml_str:
        fullpath = path
    else:
        if os.path.exists(path) and path != "" and path != ".":
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.normpath(os.path.join(basedir, path))
        if fullpath == "":
            raise ValueError("file not found")
        if not fullpath.endswith(".yml") and not fullpath.endswith(".yaml"):
            raise ValueError('task yaml file must be ".yml" or ".yaml"')
    tfObj.name = os.path.basename(fullpath)
    defined_in = fullpath
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir) :]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    tfObj.defined_in = defined_in
    if role_name != "":
        tfObj.role = role_name
    if collection_name != "":
        tfObj.collection = collection_name
    tfObj.set_key()

    task_dicts, yaml_lines = get_task_blocks(fpath=fullpath, yaml_str=yaml_str)

    if yaml_str and not yaml_lines:
        yaml_lines = yaml_str
    tfObj.yaml_lines = yaml_lines

    if task_dicts is None:
        return tfObj
    tasks = []
    for i, t_dict in enumerate(task_dicts):
        try:
            t = load_task(
                fullpath,
                i,
                t_dict,
                role_name,
                collection_name,
                yaml_lines=yaml_lines,
                parent_key=tfObj.key,
                parent_local_key=tfObj.local_key,
                basedir=basedir,
            )
            tasks.append(t)
        except TaskFormatError:
            if skip_task_format_error:
                logger.debug("this task is wrong format; skip the task in {}, index: {}; skip this".format(fullpath, i))
                continue
            else:
                raise TaskFormatError(f"Task format error found; {fullpath}, index: {i}")
        except Exception:
            logger.exception("error while loading the task at {}, index: {}".format(fullpath, i))
    tfObj.tasks = tasks

    return tfObj


# playbooks possibly include/import task files around the playbook file
# we search this type of isolated taskfile in `playbooks` and `tasks` dir
def load_taskfiles(path, basedir="", load_children=True):
    if not os.path.exists(path):
        return []

    taskfile_paths = search_taskfiles_for_playbooks(path)
    if len(taskfile_paths) == 0:
        return []

    taskfiles = []
    for taskfile_path in taskfile_paths:
        try:
            tf = load_taskfile(taskfile_path, basedir=basedir)
        except Exception:
            logger.exception("error while loading the task file at {}".format(taskfile_path))
        if load_children:
            taskfiles.append(tf)
        else:
            taskfiles.append(tf.defined_in)
    if not load_children:
        taskfiles = sorted(taskfiles)
    return taskfiles


def load_collection(
    collection_dir,
    basedir="",
    use_ansible_doc=True,
    skip_playbook_format_error=True,
    skip_task_format_error=True,
    include_test_contents=False,
    load_children=True,
):

    colObj = Collection()
    fullpath = ""
    if os.path.exists(collection_dir):
        fullpath = collection_dir
    if os.path.exists(os.path.join(basedir, collection_dir)):
        fullpath = os.path.join(basedir, collection_dir)
    if fullpath == "":
        raise ValueError("directory not found")
    parts = fullpath.split("/")
    if len(parts) < 2:
        raise ValueError("collection directory path is wrong")
    collection_name = "{}.{}".format(parts[-2], parts[-1])

    manifest_file_path = os.path.join(fullpath, "MANIFEST.json")
    if os.path.exists(manifest_file_path):
        with open(manifest_file_path, "r") as file:
            colObj.metadata = json.load(file)

        if colObj.metadata is not None and isinstance(colObj.metadata, dict):
            colObj.dependency["collections"] = colObj.metadata.get("collection_info", {}).get("dependencies", {})

    files_file_path = os.path.join(fullpath, "FILES.json")
    if os.path.exists(files_file_path):
        with open(files_file_path, "r") as file:
            colObj.files = json.load(file)

    meta_runtime_file_path = os.path.join(fullpath, "meta", "runtime.yml")
    if os.path.exists(meta_runtime_file_path):
        with open(meta_runtime_file_path, "r") as file:
            try:
                colObj.meta_runtime = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load meta/runtime.yml; {}".format(e.args[0]))

    requirements_yml_path = os.path.join(fullpath, "requirements.yml")
    if os.path.exists(requirements_yml_path):
        with open(requirements_yml_path, "r") as file:
            try:
                colObj.requirements = yaml.load(file, Loader=Loader)
            except Exception as e:
                logger.debug("failed to load requirements.yml; {}".format(e.args[0]))

    if isinstance(colObj.metadata, dict):
        license_filename = colObj.metadata.get("collection_info", {}).get("license_file", None)
        if license_filename:
            license_filepath = os.path.join(fullpath, license_filename)
            if os.path.exists(license_filepath):
                with open(license_filepath, "r") as file:
                    contents = file.read()
                    lines = contents.splitlines()
                    if len(lines) > 10:
                        contents = "\n".join(lines[:10])
                    colObj.metadata["_ari_added"] = {
                        "license_file_contents_head": contents,
                    }

    playbooks = load_playbooks(
        path=fullpath,
        basedir=basedir,
        skip_playbook_format_error=skip_playbook_format_error,
        skip_task_format_error=skip_task_format_error,
        include_test_contents=include_test_contents,
        load_children=load_children,
    )

    taskfile_paths = search_taskfiles_for_playbooks(fullpath)
    if len(taskfile_paths) > 0:
        taskfiles = []
        for taskfile_path in taskfile_paths:
            try:
                tf = load_taskfile(taskfile_path, basedir=basedir)
            except Exception:
                logger.exception("error while loading the task file at {}".format(taskfile_path))
                continue
            if load_children:
                taskfiles.append(tf)
            else:
                taskfiles.append(tf.defined_in)
        if not load_children:
            taskfiles = sorted(taskfiles)
        colObj.taskfiles = taskfiles

    roles = load_roles(
        path=fullpath,
        basedir=basedir,
        use_ansible_doc=use_ansible_doc,
        include_test_contents=include_test_contents,
        load_children=load_children,
    )

    module_files = search_module_files(fullpath)

    modules = []
    if not load_children:
        use_ansible_doc = False

    module_specs = {}
    if use_ansible_doc:
        module_specs = get_module_specs_by_ansible_doc(
            module_files=module_files,
            fqcn_prefix=collection_name,
            search_path=fullpath,
        )

    for f in module_files:
        m = None
        try:
            m = load_module(f, collection_name=collection_name, basedir=basedir, use_ansible_doc=use_ansible_doc, module_specs=module_specs)
        except Exception:
            logger.exception("error while loading the module at {}".format(f))
            continue
        if load_children:
            modules.append(m)
        else:
            modules.append(m.defined_in)
    if not load_children:
        modules = sorted(modules)
    colObj.name = collection_name
    path = collection_dir
    if basedir != "":
        if path.startswith(basedir):
            path = path[len(basedir) :]
    colObj.path = path
    colObj.playbooks = playbooks
    colObj.roles = roles
    colObj.modules = modules

    return colObj


def load_object(loadObj):
    target_type = loadObj.target_type
    path = loadObj.path
    obj = None
    if target_type == LoadType.COLLECTION:
        obj = load_collection(collection_dir=path, basedir=path, include_test_contents=loadObj.include_test_contents, load_children=False)
    elif target_type == LoadType.ROLE:
        obj = load_role(path=path, basedir=path, include_test_contents=loadObj.include_test_contents, load_children=False)
    elif target_type == LoadType.PLAYBOOK:
        basedir = ""
        target_playbook_path = ""
        if loadObj.playbook_yaml:
            target_playbook_path = path
        else:
            basedir, target_playbook_path = split_target_playbook_fullpath(path)
        if loadObj.playbook_only:
            obj = load_playbook(path=target_playbook_path, yaml_str=loadObj.playbook_yaml, basedir=basedir)
        else:
            obj = load_repository(path=basedir, basedir=basedir, target_playbook_path=target_playbook_path, load_children=False)
    elif target_type == LoadType.TASKFILE:
        basedir = ""
        target_taskfile_path = ""
        if loadObj.taskfile_yaml:
            target_taskfile_path = path
        else:
            basedir, target_taskfile_path = split_target_taskfile_fullpath(path)
        if loadObj.taskfile_only:
            obj = load_taskfile(path=target_taskfile_path, yaml_str=loadObj.taskfile_yaml, basedir=basedir)
        else:
            obj = load_repository(path=basedir, basedir=basedir, target_taskfile_path=target_taskfile_path, load_children=False)
    elif target_type == LoadType.PROJECT:
        obj = load_repository(path=path, basedir=path, load_children=False)

    if hasattr(obj, "roles"):
        loadObj.roles = obj.roles
    if hasattr(obj, "playbooks"):
        loadObj.playbooks = obj.playbooks
    if hasattr(obj, "taskfiles"):
        loadObj.taskfiles = obj.taskfiles
    if hasattr(obj, "handlers"):
        current = loadObj.taskfiles
        if not current:
            current = []
        loadObj.taskfiles = current + obj.handlers
    if hasattr(obj, "modules"):
        loadObj.modules = obj.modules

    if target_type == LoadType.ROLE:
        loadObj.roles = [obj.defined_in]
    elif target_type == LoadType.PLAYBOOK and loadObj.playbook_only:
        loadObj.playbooks = [obj.defined_in]
    elif target_type == LoadType.TASKFILE and loadObj.taskfile_only:
        loadObj.taskfiles = [obj.defined_in]

    loadObj.timestamp = datetime.datetime.utcnow().isoformat()


def find_playbook_role_module(path, use_ansible_doc=True):
    playbooks = load_playbooks(path, basedir=path, load_children=False)
    root_role = None
    try:
        root_role = load_role(path, basedir=path, use_ansible_doc=use_ansible_doc, load_children=False)
    except Exception:
        pass
    sub_roles = load_roles(path, basedir=path, use_ansible_doc=use_ansible_doc, load_children=False)
    roles = []
    if root_role and root_role.metadata:
        roles.append(".")
    if len(sub_roles) > 0:
        roles.extend(sub_roles)
    modules = load_modules(path, basedir=path, use_ansible_doc=use_ansible_doc, load_children=False)
    return playbooks, roles, modules
