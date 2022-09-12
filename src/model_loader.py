import datetime
import json
import logging
import os
import re
import yaml
from safe_glob import safe_glob
from models import (
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
    RoleInPlay,
    Task,
    TaskFile,
    TaskFormatError,
    Collection,
)
from finder import (
    find_best_repo_root_path,
    find_collection_name_of_repo,
    find_module_name,
    get_task_blocks,
    search_inventory_files,
    find_module_dirs,
    search_module_files,
    search_taskfiles_for_playbooks,
)
from awx_utils import could_be_playbook

# collection info direcotry can be something like
#   "brightcomputing.bcm-9.1.11+41615.gitfab9053.info"
collection_info_dir_re = re.compile(
    r"^[a-z0-9_]+\.[a-z0-9_]+-[0-9]+\.[0-9]+\.[0-9]+.*\.info$"
)

string_module_options_re = re.compile(
    r"[a-z0-9]+=(?:[^ ]*{{ [^ ]+ }}[^ ]*|[^ ])+"
)

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
    load_children=True,
):
    repoObj = Repository()

    repo_path = ""
    if path == "":
        # if path is empty, just load installed collections / roles
        repo_path = ""
    else:
        # otherwise, find the root path by searching playbooks
        repo_path = find_best_repo_root_path(path)
        if repo_path == "":
            repo_path = path
            logging.warning(
                'failed to find a root directory for ansible files; use "{}"'
                " but this may be wrong".format(path)
            )

    if repo_path != "":
        if my_collection_name == "":
            my_collection_name = find_collection_name_of_repo(repo_path)
        if my_collection_name != "":
            repoObj.my_collection_name = my_collection_name

    if basedir == "":
        basedir = path

    logging.info("start loading the repo {}".format(repo_path))
    logging.debug("start loading playbooks")
    repoObj.playbooks = load_playbooks(
        repo_path, basedir=basedir, load_children=load_children
    )
    logging.debug(
        "done ... {} playbooks loaded".format(len(repoObj.playbooks))
    )
    logging.debug("start loading roles")
    repoObj.roles = load_roles(
        repo_path, basedir=basedir, load_children=load_children
    )
    logging.debug("done ... {} roles loaded".format(len(repoObj.roles)))
    logging.debug(
        "start loading modules (that are defined in this repository)"
    )
    repoObj.modules = load_modules(
        repo_path,
        basedir=basedir,
        collection_name=my_collection_name,
        load_children=load_children,
    )
    logging.debug("done ... {} modules loaded".format(len(repoObj.modules)))
    logging.debug(
        "start loading taskfiles (that are defined for playbooks in this"
        " repository)"
    )
    repoObj.taskfiles = load_taskfiles(
        repo_path, basedir=basedir, load_children=load_children
    )
    logging.debug(
        "done ... {} task files loaded".format(len(repoObj.taskfiles))
    )
    logging.debug("start loading inventory files")
    repoObj.inventories = load_inventories(repo_path, basedir=basedir)
    logging.debug(
        "done ... {} inventory files loaded".format(len(repoObj.inventories))
    )
    logging.debug("start loading installed collections")
    repoObj.installed_collections = load_installed_collections(
        installed_collections_path
    )

    logging.debug(
        "done ... {} collections loaded".format(
            len(repoObj.installed_collections)
        )
    )
    logging.debug("start loading installed roles")
    repoObj.installed_roles = load_installed_roles(installed_roles_path)
    logging.debug(
        "done ... {} roles loaded".format(len(repoObj.installed_roles))
    )
    repoObj.requirements = load_requirements(path=repo_path)
    name = os.path.basename(path)
    repoObj.name = name
    _path = name
    if os.path.abspath(repo_path).startswith(os.path.abspath(path)):
        relative = os.path.abspath(repo_path)[len(os.path.abspath(path)):]
        _path = os.path.join(name, relative)
    repoObj.path = _path
    repoObj.installed_collections_path = installed_collections_path
    repoObj.installed_roles_path = installed_roles_path
    logging.info("done")

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
                c = load_collection(
                    collection_dir=collection_path, basedir=basedir
                )
                collections.append(c)
            except Exception:
                logging.exception(
                    "error while loading the collection at {}".format(
                        collection_path
                    )
                )
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
            defined_in = defined_in[len(basedir):]
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
                data = yaml.safe_load(file)
            except Exception as e:
                logging.error(
                    "failed to load this yaml file (inventory); {}".format(
                        e.args[0]
                    )
                )
    elif file_ext == ".json":
        with open(fullpath, "r") as file:
            try:
                data = json.load(file)
            except Exception as e:
                logging.error(
                    "failed to load this json file (inventory); {}".format(
                        e.args[0]
                    )
                )
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
                logging.exception(
                    "error while loading the inventory file at {}".format(
                        inventory_path
                    )
                )
    return inventories


def load_play(
    path,
    index,
    play_block_dict,
    role_name="",
    collection_name="",
    parent_key="",
    parent_local_key="",
    basedir="",
):
    pbObj = Play()
    if play_block_dict is None:
        raise ValueError("play block dict is required to load Play")
    if not isinstance(play_block_dict, dict):
        raise PlaybookFormatError(
            "this play block is not loaded as dict; maybe this is not a"
            " playbook"
        )
    data_block = play_block_dict
    if (
        "hosts" not in data_block
        and "import_playbook" not in data_block
        and "include" not in data_block
    ):
        raise PlaybookFormatError(
            'this play block does not have "hosts", "import_playbook" and'
            ' "include"; maybe this is not a playbook'
        )

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
    play_options = {}
    import_module = ""
    import_playbook = ""
    __pre_task_blocks = get_task_blocks(
        task_dict_list=data_block.get("pre_tasks", [])
    )
    __task_blocks = get_task_blocks(
        task_dict_list=data_block.get("tasks", [])
    )
    pre_task_num = len(__pre_task_blocks)
    task_num = len(__task_blocks)
    for k, v in data_block.items():
        if k == "name":
            pass
        elif k == "collections":
            pass
        elif k == "pre_tasks":
            if not isinstance(v, list):
                continue
            task_blocks = get_task_blocks(task_dict_list=v)
            if task_blocks is None:
                continue
            for i, task_dict in enumerate(task_blocks):
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
                        basedir=basedir,
                    )
                    pre_tasks.append(t)
                except TaskFormatError:
                    logging.debug(
                        "this task is wrong format; skip the task in {},"
                        " index: {}".format(path, i)
                    )
                    continue
                except Exception:
                    logging.exception(
                        "error while loading the task at {} (index={})"
                        .format(path, i)
                    )
        elif k == "tasks":
            if not isinstance(v, list):
                continue
            task_blocks = get_task_blocks(task_dict_list=v)
            if task_blocks is None:
                continue
            for i, task_dict in enumerate(task_blocks):
                _i = i + pre_task_num
                try:
                    t = load_task(
                        path=path,
                        index=_i,
                        task_block_dict=task_dict,
                        role_name=role_name,
                        collection_name=collection_name,
                        collections_in_play=collections_in_play,
                        play_index=index,
                        parent_key=pbObj.key,
                        parent_local_key=pbObj.local_key,
                        basedir=basedir,
                    )
                    tasks.append(t)
                except TaskFormatError:
                    logging.debug(
                        "this task is wrong format; skip the task in {},"
                        " index: {}".format(path, i)
                    )
                    continue
                except Exception:
                    logging.exception(
                        "error while loading the task at {} (index={})"
                        .format(path, i)
                    )
        elif k == "post_tasks":
            if not isinstance(v, list):
                continue
            task_blocks = get_task_blocks(task_dict_list=v)
            if task_blocks is None:
                continue
            for i, task_dict in enumerate(task_blocks):
                _i = i + pre_task_num + task_num
                try:
                    t = load_task(
                        path=path,
                        index=_i,
                        task_block_dict=task_dict,
                        role_name=role_name,
                        collection_name=collection_name,
                        collections_in_play=collections_in_play,
                        play_index=index,
                        parent_key=pbObj.key,
                        parent_local_key=pbObj.local_key,
                        basedir=basedir,
                    )
                    post_tasks.append(t)
                except TaskFormatError:
                    logging.debug(
                        "this task is wrong format; skip the task in {},"
                        " index: {}".format(path, i)
                    )
                    continue
                except Exception:
                    logging.exception(
                        "error while loading the task at {} (index={})"
                        .format(path, i)
                    )
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
                    logging.exception(
                        "error while loading the role in playbook at {}"
                        " (play_index={}, role_index={})".format(
                            path, pbObj.index, i
                        )
                    )
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
    pbObj.options = play_options
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
            defined_in = defined_in[len(basedir):]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    ripObj.defined_in = defined_in
    ripObj.role = role_name
    ripObj.collection = collection_name
    ripObj.role_index = role_index
    ripObj.play_index = play_index
    ripObj.collections_in_play = collections_in_play

    return ripObj


def load_playbook(path, role_name="", collection_name="", basedir=""):
    pbObj = Playbook()
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
            defined_in = defined_in[len(basedir):]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    pbObj.defined_in = defined_in
    pbObj.name = os.path.basename(fullpath)
    pbObj.role = role_name
    pbObj.collection = collection_name
    pbObj.set_key()
    data = None
    if fullpath != "":
        with open(fullpath, "r") as file:
            try:
                data = yaml.safe_load(file)
            except Exception as e:
                logging.error(
                    "failed to load this yaml file to load playbook; {}"
                    .format(e.args[0])
                )
    if data is None:
        return pbObj
    if not isinstance(data, list):
        raise PlaybookFormatError(
            "playbook must be loaded as a list, but got {}".format(
                type(data).__name__
            )
        )

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
                basedir=basedir,
            )
            plays.append(play)
        except PlaybookFormatError:
            logging.debug(
                "this play is wrong format; skip the play in {}, index: {}"
                .format(fullpath, i)
            )
            continue
        except Exception:
            logging.exception(
                "error while loading the play at {} (index={})".format(
                    fullpath, i
                )
            )
    pbObj.plays = plays

    return pbObj


def load_playbooks(path, basedir="", load_children=True):
    if path == "":
        return []
    patterns = [
        path + "/*.yml",
        path + "/*.yaml",
        path + "/playbooks/**/*.yml",
        path + "/playbooks/**/*.yaml",
    ]
    candidates = safe_glob(patterns, recursive=True)
    playbooks = []
    for fpath in candidates:
        if could_be_playbook(fpath):
            if "/roles/" in fpath:
                continue
            p = None
            try:
                p = load_playbook(fpath, basedir=basedir)
            except PlaybookFormatError as e:
                logging.debug(
                    "this file is not in a playbook format, maybe not a"
                    " playbook file: {}".format(e.args[0])
                )
                continue
            except Exception:
                logging.exception(
                    "error while loading the playbook at {}".format(fpath)
                )
            if load_children:
                playbooks.append(p)
            else:
                playbooks.append(p.defined_in)
    if not load_children:
        playbooks = sorted(playbooks)
    return playbooks


def load_role(
    path,
    name="",
    collection_name="",
    module_dir_paths=[],
    basedir="",
    load_children=True,
):
    roleObj = Role()
    fullpath = ""
    if os.path.exists(path) and path != "" and path != ".":
        fullpath = path
    if os.path.exists(os.path.join(basedir, path)):
        fullpath = os.path.normpath(os.path.join(basedir, path))
    if fullpath == "":
        raise ValueError("directory not found")
    meta_file_path = ""
    defaults_dir_path = ""
    vars_dir_path = ""
    tasks_dir_path = ""
    includes_dir_path = ""
    if fullpath != "":
        meta_file_path = os.path.join(fullpath, "meta/main.yml")
        defaults_dir_path = os.path.join(fullpath, "defaults")
        vars_dir_path = os.path.join(fullpath, "vars")
        tasks_dir_path = os.path.join(fullpath, "tasks")
        includes_dir_path = os.path.join(fullpath, "includes")
    if os.path.exists(meta_file_path):
        with open(meta_file_path, "r") as file:
            try:
                roleObj.metadata = yaml.safe_load(file)
            except Exception as e:
                logging.error(
                    "failed to load this yaml file to raed metadata; {}"
                    .format(e.args[0])
                )

            if roleObj.metadata is not None and isinstance(
                roleObj.metadata, dict
            ):
                roleObj.dependency["roles"] = roleObj.metadata.get(
                    "dependencies", []
                )
                roleObj.dependency["collections"] = roleObj.metadata.get(
                    "collections", []
                )

    requirements_yml_path = os.path.join(fullpath, "requirements.yml")
    if os.path.exists(requirements_yml_path):
        with open(requirements_yml_path, "r") as file:
            try:
                roleObj.requirements = yaml.safe_load(file)
            except Exception as e:
                logging.error(
                    "failed to load requirements.yml; {}".format(e.args[0])
                )

    parts = tasks_dir_path.split("/")
    if len(parts) < 2:
        raise ValueError("role path is wrong")
    role_name = parts[-2] if name == "" else name
    roleObj.name = role_name
    defined_in = fullpath
    if basedir != "":
        if defined_in.startswith(basedir):
            defined_in = defined_in[len(basedir):]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    roleObj.defined_in = defined_in
    collection = ""
    fqcn = role_name
    if collection_name != "":
        collection = collection_name
        fqcn = "{}.{}".format(collection_name, role_name)
    roleObj.collection = collection
    roleObj.fqcn = fqcn
    roleObj.set_key()

    if os.path.exists(os.path.join(fullpath, "playbooks")):
        playbook_files = safe_glob(
            fullpath + "/playbooks/**/*.yml", recursive=True
        )
        playbooks = []
        for f in playbook_files:
            p = None
            try:
                p = load_playbook(
                    f,
                    role_name=role_name,
                    collection_name=collection_name,
                    basedir=basedir,
                )
            except PlaybookFormatError as e:
                logging.debug(
                    "this file is not in a playbook format, maybe not a"
                    " playbook file: {}".format(e.args[0])
                )
                continue
            except Exception:
                logging.exception(
                    "error while loading the playbook at {}".format(f)
                )
            if load_children:
                playbooks.append(p)
            else:
                playbooks.append(p.defined_in)
        if not load_children:
            playbooks = sorted(playbooks)
        roleObj.playbooks = playbooks

    if os.path.exists(defaults_dir_path):
        patterns = [
            defaults_dir_path + "/**/*.yml",
            defaults_dir_path + "/**/*.yaml",
        ]
        defaults_yaml_files = safe_glob(patterns, recursive=True)
        default_variables = {}
        for fpath in defaults_yaml_files:
            with open(fpath, "r") as file:
                try:
                    vars_in_yaml = yaml.safe_load(file)
                    if vars_in_yaml is None:
                        continue
                    if not isinstance(vars_in_yaml, dict):
                        continue
                    default_variables.update(vars_in_yaml)
                except Exception as e:
                    logging.error(
                        "failed to load this yaml file to raed default"
                        " variables; {}".format(e.args[0])
                    )
        roleObj.default_variables = default_variables

    if os.path.exists(vars_dir_path):
        patterns = [vars_dir_path + "/**/*.yml", vars_dir_path + "/**/*.yaml"]
        vars_yaml_files = safe_glob(patterns, recursive=True)
        variables = {}
        for fpath in vars_yaml_files:
            with open(fpath, "r") as file:
                try:
                    vars_in_yaml = yaml.safe_load(file)
                    if vars_in_yaml is None:
                        continue
                    if not isinstance(vars_in_yaml, dict):
                        continue
                    variables.update(vars_in_yaml)
                except Exception as e:
                    logging.error(
                        "failed to load this yaml file to raed variables; {}"
                        .format(e.args[0])
                    )
        roleObj.variables = variables

    if not os.path.exists(tasks_dir_path):
        # a role possibly has no tasks
        return roleObj

    modules = []
    module_files = search_module_files(fullpath, module_dir_paths)
    for module_file_path in module_files:
        m = None
        try:
            m = load_module(
                module_file_path,
                collection_name=collection_name,
                role_name=fqcn,
                basedir=basedir,
            )
        except Exception:
            logging.exception(
                "error while loading the module at {}".format(
                    module_file_path
                )
            )
        if load_children:
            modules.append(m)
        else:
            modules.append(m.defined_in)
    if not load_children:
        modules = sorted(modules)
    roleObj.modules = modules

    patterns = [tasks_dir_path + "/**/*.yml", tasks_dir_path + "/**/*.yaml"]
    # ansible.network collection has this type of another taskfile directory
    if os.path.exists(includes_dir_path):
        patterns.extend(
            [
                includes_dir_path + "/**/*.yml",
                includes_dir_path + "/**/*.yaml",
            ]
        )
    task_yaml_files = safe_glob(patterns, recursive=True)

    taskfiles = []
    for task_yaml_path in task_yaml_files:
        try:
            tf = load_taskfile(
                task_yaml_path,
                role_name=fqcn,
                collection_name=collection_name,
                basedir=basedir,
            )
        except Exception:
            logging.exception(
                "error while loading the task file at {}".format(
                    task_yaml_path
                )
            )
        if load_children:
            taskfiles.append(tf)
        else:
            taskfiles.append(tf.defined_in)
    if not load_children:
        taskfiles = sorted(taskfiles)
    roleObj.taskfiles = taskfiles

    return roleObj


def load_roles(path, basedir="", load_children=True):
    if path == "":
        return []
    roles_patterns = ["roles", "playbooks/roles", "playbook/roles"]
    roles_dir_path = ""
    for r_p in roles_patterns:
        candidate = os.path.join(path, r_p)
        if os.path.exists(candidate):
            roles_dir_path = candidate
            break
    if roles_dir_path == "":
        return []
    dirs = os.listdir(roles_dir_path)
    roles = []
    for dir_name in dirs:
        role_dir = os.path.join(roles_dir_path, dir_name)
        try:
            r = load_role(role_dir, basedir=basedir)
        except Exception:
            logging.exception(
                "error while loading the role at {}".format(role_dir)
            )
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
                requirements = yaml.safe_load(file)
            except Exception as e:
                logging.error(
                    "failed to load requirements.yml; {}".format(e.args[0])
                )
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
        role_meta_files = safe_glob(
            role_path + "/**/meta/main.yml", recursive=True
        )

        roles_root_dirs = set(
            [
                f.split("/roles/")[-2]
                for f in role_meta_files
                if "/roles/" in f
            ]
        )
        module_dirs = []
        for role_root_dir in roles_root_dirs:
            moddirs = find_module_dirs(role_root_dir)
            module_dirs.extend(moddirs)

        for i, role_meta_file in enumerate(role_meta_files):
            role_dir_path = role_meta_file.replace("/meta/main.yml", "")
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
                logging.exception(
                    "error while loading the role at {}".format(role_dir_path)
                )
    return roles


def load_module(
    module_file_path, collection_name="", role_name="", basedir=""
):
    moduleObj = Module()
    if module_file_path == "":
        raise ValueError("require module file path to load a Module")
    file_name = os.path.basename(module_file_path)
    module_name = file_name.replace(".py", "")
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
            defined_in = defined_in[len(basedir):]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    moduleObj.defined_in = defined_in
    moduleObj.set_key()

    return moduleObj


# modules in a SCM repo should be in `library` dir in the best practice case
# https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html
# however, it is often defined in `plugins/modules` directory,
# so we search both the directories
def load_modules(path, basedir="", collection_name="", load_children=True):
    if path == "":
        return []
    if not os.path.exists(path):
        return []
    module_files = search_module_files(path)

    if len(module_files) == 0:
        return []
    modules = []
    for module_file_path in module_files:
        m = None
        try:
            m = load_module(
                module_file_path,
                collection_name=collection_name,
                basedir=basedir,
            )
        except Exception:
            logging.exception(
                "error while loading the module at {}".format(
                    module_file_path
                )
            )
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
    basedir="",
):

    taskObj = Task()
    fullpath = ""
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
        raise TaskFormatError(
            "this task block is not loaded as dict; maybe this is not a task"
        )
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

    taskObj.set_yaml_lines(fullpath, task_name, module_name, module_options)

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
            defined_in = defined_in[len(basedir):]
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

    # if the Task is set_fact, set variables too
    if module_short_name == "set_fact":
        if isinstance(module_options, dict):
            variables.update(module_options)

    registered_variables = {}
    # set variables if this task register a new var
    if "register" in task_options:
        register_var_name = task_options.get("register", "")
        if (
            register_var_name is not None
            and isinstance(register_var_name, str)
            and register_var_name != ""
        ):
            registered_variables.update({register_var_name: taskObj.key})

    # set loop variables when loop / with_xxxx are there
    loop_info = {}
    for k in task_options:
        if k in loop_task_option_names:
            loop_var = task_options.get("loop_control", {}).get(
                "loop_var", "item"
            )
            loop_info[loop_var] = task_options.get(k, [])

    taskObj.options = task_options
    taskObj.variables = variables
    taskObj.registered_variables = registered_variables
    taskObj.loop = loop_info
    taskObj.module = module_name
    taskObj.module_options = module_options

    return taskObj


def load_taskfile(path, role_name="", collection_name="", basedir=""):
    tfObj = TaskFile()

    fullpath = ""
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
            defined_in = defined_in[len(basedir):]
            if defined_in.startswith("/"):
                defined_in = defined_in[1:]
    tfObj.defined_in = defined_in
    if role_name != "":
        tfObj.role = role_name
    if collection_name != "":
        tfObj.collection = collection_name
    tfObj.set_key()

    task_dicts = get_task_blocks(fpath=fullpath)
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
                parent_key=tfObj.key,
                parent_local_key=tfObj.local_key,
                basedir=basedir,
            )
            tasks.append(t)
        except TaskFormatError:
            logging.debug(
                "this task is wrong format; skip the task in {}, index: {}"
                .format(fullpath, i)
            )
            continue
        except Exception:
            logging.exception(
                "error while loading the task at {}, index: {}".format(
                    fullpath, i
                )
            )
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
            logging.exception(
                "error while loading the task file at {}".format(
                    taskfile_path
                )
            )
        if load_children:
            taskfiles.append(tf)
        else:
            taskfiles.append(tf.defined_in)
    if not load_children:
        taskfiles = sorted(taskfiles)
    return taskfiles


def load_collection(collection_dir, basedir="", load_children=True):
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
            colObj.dependency["collections"] = colObj.metadata.get(
                "dependencies", {}
            )

    requirements_yml_path = os.path.join(fullpath, "requirements.yml")
    if os.path.exists(requirements_yml_path):
        with open(requirements_yml_path, "r") as file:
            try:
                colObj.requirements = yaml.safe_load(file)
            except Exception as e:
                logging.error(
                    "failed to load requirements.yml; {}".format(e.args[0])
                )

    playbook_files = safe_glob(
        fullpath + "/playbooks/**/*.yml", recursive=True
    )
    playbooks = []
    for f in playbook_files:
        p = None
        try:
            p = load_playbook(
                f, collection_name=collection_name, basedir=basedir
            )
        except PlaybookFormatError as e:
            logging.debug(
                "this file is not in a playbook format, maybe not a playbook"
                " file: {}".format(e.args[0])
            )
            continue
        except Exception:
            logging.exception(
                "error while loading the playbook at {}".format(f)
            )
            continue
        if load_children:
            playbooks.append(p)
        else:
            playbooks.append(p.defined_in)
    if not load_children:
        playbooks = sorted(playbooks)

    taskfile_paths = search_taskfiles_for_playbooks(fullpath)
    if len(taskfile_paths) > 0:
        taskfiles = []
        for taskfile_path in taskfile_paths:
            try:
                tf = load_taskfile(taskfile_path, basedir=basedir)
            except Exception:
                logging.exception(
                    "error while loading the task file at {}".format(
                        taskfile_path
                    )
                )
                continue
            if load_children:
                taskfiles.append(tf)
            else:
                taskfiles.append(tf.defined_in)
        if not load_children:
            taskfiles = sorted(taskfiles)
        colObj.taskfiles = taskfiles

    role_tasks_files = safe_glob(
        fullpath + "/roles/*/tasks/main.yml", recursive=True
    )
    roles = []
    for f in role_tasks_files:
        role_dir_path = f.replace("/tasks/main.yml", "")
        try:
            r = load_role(
                role_dir_path,
                collection_name=collection_name,
                basedir=basedir,
            )
        except Exception:
            logging.exception("error while loading the role at {}".format(f))
            continue
        if load_children:
            roles.append(r)
        else:
            roles.append(r.defined_in)
    if not load_children:
        roles = sorted(roles)

    module_files = search_module_files(fullpath)
    modules = []
    for f in module_files:
        m = None
        try:
            m = load_module(
                f, collection_name=collection_name, basedir=basedir
            )
        except Exception:
            logging.exception(
                "error while loading the module at {}".format(f)
            )
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
            path = path[len(basedir):]
    colObj.path = path
    colObj.playbooks = playbooks
    colObj.roles = roles
    colObj.modules = modules

    return colObj


def load_object(loadObj):
    target_type = loadObj.target_type
    path = loadObj.path
    obj = None
    if target_type == LoadType.COLLECTION_TYPE:
        obj = load_collection(
            collection_dir=path, basedir=path, load_children=False
        )
    elif target_type == LoadType.ROLE_TYPE:
        obj = load_role(path=path, basedir=path, load_children=False)
    elif target_type == LoadType.PLAYBOOK_TYPE:
        obj = load_playbook(
            path=path, role_name="", collection_name="", basedir=path
        )
    elif target_type == LoadType.PROJECT_TYPE:
        obj = load_repository(path=path, basedir=path, load_children=False)

    if hasattr(obj, "roles"):
        loadObj.roles = obj.roles
    if hasattr(obj, "playbooks"):
        loadObj.playbooks = obj.playbooks
    if hasattr(obj, "taskfiles"):
        loadObj.taskfiles = obj.taskfiles
    if hasattr(obj, "modules"):
        loadObj.modules = obj.modules
    loadObj.timestamp = datetime.datetime.utcnow().isoformat()
