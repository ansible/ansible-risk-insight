from dataclasses import dataclass, field
import copy
import json
import jsonpickle
import logging
from keyutil import (
    set_collection_key,
    set_module_key,
    set_play_key,
    set_playbook_key,
    set_repository_key,
    set_role_key,
    set_task_key,
    set_taskfile_key,
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
        resolver.apptly(self)

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
    PROJECT_TYPE = "project"
    COLLECTION_TYPE = "collection"
    ROLE_TYPE = "role"
    PLAYBOOK_TYPE = "playbook"
    UNKNOWN_TYPE = "unknown"

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

# def get_repo_root(filepath):
#     git_root = ""
#     try:
#         repo = git.Repo(path=filepath, search_parent_directories=True)
#         git_root = repo.git.rev_parse("--show-toplevel")
#     except:
#         # this path may not be a git repository
#         return ""
#     return git_root

@dataclass
class ObjectList(Resolvable):
    items: list = field(default_factory=list)
    _dict: dict = field(default_factory=dict)

    def dump(self, fpath=""):
        return self.to_json(fpath=fpath)

    def to_json(self, fpath=""):
        lines = [
            jsonpickle.encode(obj, make_refs=False) for obj in self.items
        ]
        json_str = "\n".join(lines)
        if fpath != "":
            open(fpath, "w").write(json_str)
        return json_str

    def from_json(self, json_str="", fpath=""):
        if fpath != "":
            json_str = open(fpath, "r").read()
        lines = json_str.splitlines()
        items = [jsonpickle.decode(obj_str) for obj_str in lines]
        self.items = items
        self._update_dict()
        return copy.deepcopy(self)

    def add(self, obj):
        self.items.append(obj)
        self._update_dict()
        return

    def merge(self, obj_list):
        if not isinstance(obj_list, ObjectList):
            raise ValueError(
                "obj_list must be an instance of ObjectList, but got {}"
                .format(type(obj_list).__name__)
            )
        self.items.extend(obj_list.items)
        self._update_dict()
        return

    def find_by_attr(self, key, val):
        found = [
            obj for obj in self.items if obj.__dict__.get(key, None) == val
        ]
        return found

    def find_by_type(self, type):
        return [
            obj
            for obj in self.items
            if hasattr(obj, "type") and obj.type == type
        ]

    def find_by_key(self, key):
        return self._dict.get(key, None)

    def contains(self, key="", obj=None):
        if obj is not None:
            key = obj.key
        return self.find_by_key(key) is not None

    def _update_dict(self):
        for obj in self.items:
            if obj.key not in self._dict:
                self._dict[obj.key] = obj
        return

    @property
    def resolver_targets(self):
        return self.items

@dataclass
class Module(JSONSerializable, Resolvable):
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
class Collection(JSONSerializable, Resolvable):
    type: str = "collection"
    name: str = ""
    path: str = ""
    key: str = ""
    local_key: str = ""
    metadata: dict = field(default_factory=dict)
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
        module_keys = [
            m.key if isinstance(m, Module) else m for m in self.modules
        ]
        self.modules = sorted(module_keys)

        playbook_keys = [
            p.key if isinstance(p, Playbook) else p for p in self.playbooks
        ]
        self.playbooks = sorted(playbook_keys)

        role_keys = [r.key if isinstance(r, Role) else r for r in self.roles]
        self.roles = sorted(role_keys)

        taskfile_keys = [
            tf.key if isinstance(tf, TaskFile) else tf
            for tf in self.taskfiles
        ]
        self.taskfiles = sorted(taskfile_keys)
        return self

    @property
    def resolver_targets(self):
        return self.playbooks + self.taskfiles + self.roles + self.modules

class ExecutableType:
    MODULE_TYPE = "Module"
    ROLE_TYPE = "Role"
    TASKFILE_TYPE = "TaskFile"

@dataclass
class Task(JSONSerializable, Resolvable):
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

    resolved_variables: list = field(default_factory=list)
    resolved_module_options: dict = field(default_factory=dict)

    annotations: dict = field(default_factory=dict)

    def set_yaml_lines(
        self, fullpath="", task_name="", module_name="", module_options=None
    ):
        if module_name == "":
            return
        elif task_name == "" and module_options is None:
            return
        found_line_num = -1
        lines = open(fullpath, "r").read().splitlines()
        for i, line in enumerate(lines):
            if task_name in line:
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
        if (
            begin_line_num < 0
            or end_line_num > len(lines)
            or begin_line_num > end_line_num
        ):
            return
        self.yaml_lines = "\n".join(lines[begin_line_num: end_line_num + 1])
        self.line_num_in_file = [begin_line_num + 1, end_line_num + 1]
        return

    def set_key(self, parent_key="", parent_local_key=""):
        set_task_key(self, parent_key, parent_local_key)

    def children_to_key(self):
        return self

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
class TaskFile(JSONSerializable, Resolvable):
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
class Role(JSONSerializable, Resolvable):
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
        module_keys = [
            m.key if isinstance(m, Module) else m for m in self.modules
        ]
        self.modules = sorted(module_keys)

        playbook_keys = [
            p.key if isinstance(p, Playbook) else p for p in self.playbooks
        ]
        self.playbooks = sorted(playbook_keys)

        taskfile_keys = [
            tf.key if isinstance(tf, TaskFile) else tf
            for tf in self.taskfiles
        ]
        self.taskfiles = sorted(taskfile_keys)
        return self

    @property
    def resolver_targets(self):
        return self.taskfiles + self.modules

@dataclass
class RoleInPlay(JSONSerializable, Resolvable):
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
class Play(JSONSerializable, Resolvable):
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
        pre_task_keys = [
            t.key if isinstance(t, Task) else t for t in self.pre_tasks
        ]
        self.pre_tasks = pre_task_keys

        task_keys = [t.key if isinstance(t, Task) else t for t in self.tasks]
        self.tasks = task_keys

        post_task_keys = [
            t.key if isinstance(t, Task) else t for t in self.post_tasks
        ]
        self.post_tasks = post_task_keys
        return self

    @property
    def id(self):
        return json.dumps({"path": self.defined_in, "index": self.index})

    @property
    def resolver_targets(self):
        return self.pre_tasks + self.tasks + self.roles

@dataclass
class Playbook(JSONSerializable, Resolvable):
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
        play_keys = [
            play.key if isinstance(play, Play) else play
            for play in self.plays
        ]
        self.plays = play_keys
        return self

    @property
    def resolver_targets(self):
        if "plays" in self.__dict__:
            return self.plays
        else:
            return self.roles + self.tasks

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
class Repository(JSONSerializable, Resolvable):
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
        module_keys = [
            m.key if isinstance(m, Module) else m for m in self.modules
        ]
        self.modules = sorted(module_keys)

        playbook_keys = [
            p.key if isinstance(p, Playbook) else p for p in self.playbooks
        ]
        self.playbooks = sorted(playbook_keys)

        taskfile_keys = [
            tf.key if isinstance(tf, TaskFile) else tf
            for tf in self.taskfiles
        ]
        self.taskfiles = sorted(taskfile_keys)

        role_keys = [r.key if isinstance(r, Role) else r for r in self.roles]
        self.roles = sorted(role_keys)
        return self

    @property
    def resolver_targets(self):
        return (
            self.playbooks
            + self.roles
            + self.modules
            + self.installed_roles
            + self.installed_collections
        )


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
