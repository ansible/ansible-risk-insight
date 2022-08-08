from dataclasses import dataclass, field
from gc import collect
from unicodedata import category
import io
import re
import os
import codecs
from urllib.robotparser import RobotFileParser
import yaml
import glob
import copy
import json
import datetime
import jsonpickle
import logging
import git
from safe_glob import safe_glob


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


valid_playbook_re = re.compile(r'^\s*?-?\s*?(?:hosts|include|import_playbook):\s*?.*?$')
module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

# collection info direcotry is something line "brightcomputing.bcm-9.1.11+41615.gitfab9053.info"
collection_info_dir_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+-[0-9]+\.[0-9]+\.[0-9]+.*\.info$')

# module options might be a str like below
#     community.general.ufw: port={{ item }} proto=tcp rule=allow
string_module_options_re = re.compile(r'[a-z0-9]+=(?:[^ ]*{{ [^ ]+ }}[^ ]*|[^ ])+')

module_dir_patterns = [
    "library",
    "plugins/modules",
    "plugins/actions",
]

playbook_taskfile_dir_patterns = [
    "tasks",
    "playbooks"
]

loop_task_option_names = [
    "loop",
    "with_list",
    "with_items",
    # TODO: support the following
    "with_indexed_items",
    "with_flattened",
    "with_together",
    "with_dict",
    "with_sequence",
    "with_subelements",
    "with_nested",
    "with_cartesian",
    "with_random_choice",
]

key_delimiter = ":"
object_delimiter = "#"

def make_global_key_prefix(collection, role):
    key_prefix = ""
    if collection != "":
        key_prefix = "collection{}{}{}".format(key_delimiter, collection, object_delimiter)
    elif role != "":
        key_prefix = "role{}{}{}".format(key_delimiter, role, object_delimiter)
    return key_prefix

def detect_type(key=""):
    return key.split(object_delimiter)[-1].split(key_delimiter)[0]

class PlaybookFormatError(Exception):
    pass

class TaskFileFormatError(Exception):
    pass

class TaskFormatError(Exception):
    pass

class TaskTraverseLoopError(Exception):
    pass


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

with open('task_keywords.txt', 'r') as f:
    TaskKeywordSet(set(f.read().splitlines()))

with open('builtin-modules.txt', 'r') as f:
    BuiltinModuleSet(set(f.read().splitlines()))

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
        if not hasattr(resolver, 'apply'):
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

        # apply resolver again here because some attributes was not set at first
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

    def run(self, output_path=""):
        obj = None
        if self.target_type == LoadType.COLLECTION_TYPE:
            obj = Collection()
            obj.load(collection_dir=self.path, basedir=self.path, load_children=False)
        elif self.target_type == LoadType.ROLE_TYPE:
            obj = Role()
            obj.load(path=self.path, basedir=self.path, load_children=False)
        elif self.target_type == LoadType.PLAYBOOK_TYPE:
            obj = Playbook()
            obj.load(path=self.path, role_name="", collection_name="", basedir=self.path)
        elif self.target_type == LoadType.PROJECT_TYPE:
            obj = Repository()
            obj.load(path=self.path, basedir=self.path, load_children=False)

        if hasattr(obj, "roles"):
            self.roles = obj.roles
        if hasattr(obj, "playbooks"):
            self.playbooks = obj.playbooks
        if hasattr(obj, "taskfiles"):
            self.taskfiles = obj.taskfiles
        if hasattr(obj, "modules"):
            self.modules = obj.modules
        self.timestamp = datetime.datetime.utcnow().isoformat()

        json_str = self.dump()
        if output_path != "":
            with open(output_path, "w") as file:
                file.write(json_str)
        else:
            print(json_str)

def get_repo_root(filepath):
    git_root = ""
    try:
        repo = git.Repo(path=filepath, search_parent_directories=True)
        git_root = repo.git.rev_parse("--show-toplevel")
    except:
        # this path may not be a git repository
        return ""
    return git_root

@dataclass
class ObjectList(Resolvable):
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
            raise ValueError("obj_list must be an instance of ObjectList, but got {}".format(type(obj_list).__name__))
        self.items.extend(obj_list.items)
        self._update_dict()
        return

    def find_by_attr(self, key, val):
        found = [obj for obj in self.items if obj.__dict__.get(key, None) == val]
        return found

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
    name: str = ""
    fqcn: str = ""
    key: str = ""
    local_key: str = ""
    collection: str = ""
    role: str = ""
    defined_in: str = ""
    builtin: bool = False
    used_in: list = field(default_factory=list) # resolved later

    annotations: dict = field(default_factory=dict)

    def load(self, module_file_path, collection_name="", role_name="", basedir=""):
        if module_file_path == "":
            raise ValueError("require module file path to load a Module")
        file_name = os.path.basename(module_file_path)
        module_name = file_name.replace(".py", "")
        self.name = module_name
        if collection_name != "":
            self.collection = collection_name
            self.fqcn = "{}.{}".format(collection_name, module_name)
        elif role_name != "":
            self.role = role_name
            self.fqcn = module_name # if module is defined in a role, it does not have fqcn and just called in the role
        defined_in = module_file_path
        if basedir != "":
            if defined_in.startswith(basedir):
                defined_in = defined_in[len(basedir):]
                if defined_in.startswith("/"):
                    defined_in = defined_in[1:]
        self.defined_in = defined_in
        self.set_key()

    def set_key(self):
        global_key_prefix = make_global_key_prefix(self.collection, self.role)
        global_key = "{}{}{}{}".format(global_key_prefix, type(self).__name__.lower(), key_delimiter, self.fqcn.lower())
        local_key = "{}{}{}".format(type(self).__name__.lower(), key_delimiter, self.defined_in.lower())
        self.key = global_key
        self.local_key = local_key

    def children_to_key(self):
        pass

    @property
    def resolver_targets(self):
        return None

@dataclass
class Collection(JSONSerializable, Resolvable):
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

    def load(self, collection_dir, basedir="", load_children=True):
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
                self.metadata = json.load(file)
            
            if self.metadata is not None and isinstance(self.metadata, dict):
                self.dependency["collections"] = self.metadata.get("dependencies", {})

        requirements_yml_path = os.path.join(fullpath, "requirements.yml")
        if os.path.exists(requirements_yml_path):
            with open(requirements_yml_path, "r") as file:
                try:
                    self.requirements = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load requirements.yml; {}".format(e.args[0]))
        
        playbook_files = safe_glob(fullpath + "/playbooks/**/*.yml", recursive=True)
        playbooks = []
        for f in playbook_files:
            p = Playbook()
            try:
                p.load(f, collection_name=collection_name, basedir=basedir)
            except PlaybookFormatError as e:
                logging.warning("this file is not in a playbook format, maybe not a playbook file: {}".format(e.args[0]))
                continue
            except:
                logging.exception("error while loading the playbook at {}".format(f))
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
                tf = TaskFile()
                try:
                    tf.load(taskfile_path, basedir=basedir)
                except:
                    logging.exception("error while loading the task file at {}".format(taskfile_path))
                    continue
                if load_children:
                    taskfiles.append(tf)
                else:
                    taskfiles.append(tf.defined_in)
            if not load_children:
                taskfiles = sorted(taskfiles)
            self.taskfiles = taskfiles

        role_tasks_files = safe_glob(fullpath + "/roles/*/tasks/main.yml", recursive=True)
        roles = []
        for f in role_tasks_files:
            role_dir_path = f.replace("/tasks/main.yml", "")
            r = Role()
            try:
                r.load(role_dir_path, collection_name=collection_name, basedir=basedir)
            except:
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
            m = Module()
            try:
                m.load(f, collection_name=collection_name, basedir=basedir)
            except:
                logging.exception("error while loading the module at {}".format(f))
                continue
            if load_children:
                modules.append(m)
            else:
                modules.append(m.defined_in)
        if not load_children:
            modules = sorted(modules)
        self.name = collection_name
        path = collection_dir
        if basedir != "":
            if path.startswith(basedir):
                path = path[len(basedir):]
        self.path = path
        self.playbooks = playbooks
        self.roles = roles
        self.modules = modules

    def set_key(self):
        global_key = "{}{}{}".format(type(self).__name__.lower(), key_delimiter, self.name.lower())
        local_key = global_key
        self.key = global_key
        self.local_key = local_key

    def children_to_key(self):
        module_keys = [m.key if isinstance(m, Module) else m  for m in self.modules]
        self.modules = module_keys

        playbook_keys = [p.key if isinstance(p, Playbook) else p for p in self.playbooks]
        self.playbooks = playbook_keys

        role_keys = [r.key if isinstance(r, Role) else r for r in self.roles]
        self.roles = role_keys

        taskfile_keys = [tf.key if isinstance(tf, TaskFile) else tf for tf in self.taskfiles]
        self.taskfiles = taskfile_keys

    @property
    def resolver_targets(self):
        return self.playbooks + self.taskfiles + self.roles + self.modules

class ExecutableType:
    MODULE_TYPE = "Module"
    ROLE_TYPE = "Role"
    TASKFILE_TYPE = "TaskFile"

@dataclass
class Task(JSONSerializable, Resolvable):
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
    options: dict = field(default_factory=dict)
    module_options: dict = field(default_factory=dict)
    executable: str = ""
    executable_type: str = ""
    collections_in_play: list = field(default_factory=list)

    resolved_name: str = ""  # FQCN for Module and Role. Or a file path for TaskFile.  resolved later
    possible_candidates: list = field(default_factory=list) # candidates of resovled_name

    annotations: dict = field(default_factory=dict)

    def load(self, path, index, task_block_dict, role_name="", collection_name="", collections_in_play=[], play_index=-1, parent_key="", parent_local_key="", basedir=""):
        fullpath = ""
        if os.path.exists(path):
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.join(basedir, path)
        if fullpath == "":
            raise ValueError("file not found")
        if not fullpath.endswith(".yml") and not fullpath.endswith(".yaml"):
            raise ValueError("task yaml file must be \".yml\" or \".yaml\"")
        if task_block_dict is None:
            raise ValueError("task block dict is required to load Task")
        if not isinstance(task_block_dict, dict):
            raise TaskFormatError("this task block is not loaded as dict; maybe this is not a task")
        data_block = task_block_dict
        task_name = ""
        module_name = self.find_module_name([k for k in data_block.keys()])
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
                elif module_short_name in ["import_tasks", "include_tasks", "include"]:
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
        
        # set loop variables when loop / with_xxxx are there
        loop_info = {}
        for k in task_options:
            if k in loop_task_option_names:
                loop_var = task_options.get("loop_control", {}).get("loop_var", "item")
                loop_info[loop_var] = task_options.get(k, [])

        self.name = task_name
        self.role = role_name
        self.collection = collection_name
        self.options = task_options
        self.variables = variables
        self.loop = loop_info
        self.module = module_name
        self.module_options = module_options
        defined_in = fullpath
        if basedir != "":
            if defined_in.startswith(basedir):
                defined_in = defined_in[len(basedir):]
                if defined_in.startswith("/"):
                    defined_in = defined_in[1:]
        self.defined_in = defined_in 
        self.index = index
        self.play_index = play_index
        self.executable = executable
        self.executable_type = executable_type
        self.collections_in_play = collections_in_play
        self.set_key(parent_key, parent_local_key)

    def set_key(self, parent_key="", parent_local_key=""):
        index_info = "[{}]".format(self.index)
        global_key = "{}{}{}{}{}".format(parent_key, object_delimiter, type(self).__name__.lower(), key_delimiter, index_info)
        local_key = "{}{}{}{}{}".format(parent_local_key, object_delimiter, type(self).__name__.lower(), key_delimiter, index_info)
        self.key = global_key
        self.local_key = local_key

    def find_module_name(self, keys):
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

    def children_to_key(self):
        pass

    @property
    def id(self):
        return json.dumps({"path":self.defined_in, "index": self.index, "play_index": self.play_index})

    @property
    def resolver_targets(self):
        return None

@dataclass
class TaskFile(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    key: str = ""
    local_key: str = ""
    tasks: list = field(default_factory=list)
    role: str = ""  # role name of this task file; this might be empty because a task file can be defined out of roles
    collection: str = ""

    used_in: list = field(default_factory=list) # resolved later

    annotations: dict = field(default_factory=dict)

    variables: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)

    def load(self, path, role_name="", collection_name="", basedir=""):
        fullpath = ""
        if os.path.exists(path):
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.join(basedir, path)
        if fullpath == "":
            raise ValueError("file not found")
        if not fullpath.endswith(".yml") and not fullpath.endswith(".yaml"):
            raise ValueError("task yaml file must be \".yml\" or \".yaml\"")
        self.name = os.path.basename(fullpath)
        defined_in = fullpath
        if basedir != "":
            if defined_in.startswith(basedir):
                defined_in = defined_in[len(basedir):]
                if defined_in.startswith("/"):
                    defined_in = defined_in[1:]
        self.defined_in = defined_in
        if role_name != "":
            self.role = role_name
        if collection_name != "":
            self.collection = collection_name
        self.set_key()

        task_dicts = get_task_blocks(fpath=fullpath)
        if task_dicts is None:
            return
        tasks = []
        for i, t_dict in enumerate(task_dicts):
            t = Task()
            try:
                t.load(fullpath, i, t_dict, role_name, collection_name, parent_key=self.key, parent_local_key=self.local_key, basedir=basedir)
            except TaskFormatError:
                logging.warning("this task is wrong format; skip the task in {}, index: {}".format(fullpath, i))
                continue
            except:
                logging.exception("error while loading the task at {}, index: {}".format(fullpath, i))
            tasks.append(t)
        self.tasks = tasks
        

    def set_key(self):
        global_key_prefix = make_global_key_prefix(self.collection, self.role)
        global_key = "{}{}{}{}".format(global_key_prefix, type(self).__name__.lower(), key_delimiter, self.defined_in.lower())
        local_key = "{}{}{}".format(type(self).__name__.lower(), key_delimiter, self.defined_in.lower())
        self.key = global_key
        self.local_key = local_key

    def children_to_key(self):
        task_keys = [t.key if isinstance(t, Task) else t for t in self.tasks]
        self.tasks = task_keys

    @property
    def resolver_targets(self):
        return self.tasks

def get_task_blocks(fpath="", task_dict_list=None):
    d = None
    if fpath != "":
        if not os.path.exists(fpath):
            return None
        with open(fpath , "r") as file:
            try:
                d = yaml.safe_load(file)
            except Exception as e:
                logging.error("failed to load this yaml file to get task blocks; {}".format(e.args[0]))
                return None
    elif task_dict_list is not None:
        d = task_dict_list
    else:
        return None
    if d is None:
        return None
    if not isinstance(d, list):
        return None
    tasks = []
    for task_dict in d:
        task_dict_loop = flatten_block_tasks(task_dict)
        tasks.extend(task_dict_loop)
    return tasks

# extract all tasks by flattening block tasks recursively
# a block task like below will be flattened like [some_module1, some_module2, some_module3]
# 
# - block:
#     - some_module1:
#     - block:
#         - some_module2
#         - some_module3
# 
def flatten_block_tasks(task_dict):
    if task_dict is None:
        return []
    tasks = []
    if "block" in task_dict:
        tasks_in_block = task_dict.get("block", [])
        if isinstance(tasks_in_block, list):
            for t_dict in tasks_in_block:
                tasks_in_item = flatten_block_tasks(t_dict)
                tasks.extend(tasks_in_item)
        else:
            tasks = [task_dict]
    else:
        tasks = [task_dict]
    return tasks

@dataclass
class Role(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    key: str = ""
    local_key: str = ""
    fqcn: str = ""
    metadata: dict = field(default_factory=dict)
    collection: str = ""
    playbooks: list = field(default_factory=list)
    taskfiles: list = field(default_factory=list)     # 1 role can have multiple task yamls
    modules: list = field(default_factory=list)     # roles/xxxx/library/zzzz.py can be called as module zzzz
    dependency: dict = field(default_factory=dict)
    requirements: dict = field(default_factory=dict)

    source: str = "" # collection/scm repo/galaxy

    annotations: dict = field(default_factory=dict)

    default_variables: dict = field(default_factory=dict)
    variables: dict = field(default_factory=dict)
    loop: dict = field(default_factory=dict)    # key: loop_var (default "item"), value: list/dict of item value
    options: dict = field(default_factory=dict)

    def load(self, path, collection_name="", module_dir_paths=[], basedir="", load_children=True):
        fullpath = ""
        if os.path.exists(path):
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.join(basedir, path)
        if fullpath == "":
            raise ValueError("directory not found")
        meta_file_path = ""
        defaults_dir_path = ""
        tasks_dir_path = ""
        includes_dir_path = ""
        if path != "":
            meta_file_path = os.path.join(fullpath, "meta/main.yml")
            defaults_dir_path = os.path.join(fullpath, "defaults")
            tasks_dir_path = os.path.join(fullpath, "tasks")
            includes_dir_path = os.path.join(fullpath, "includes")
        
        if os.path.exists(meta_file_path):
            with open(meta_file_path, "r") as file:
                try:
                    self.metadata = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load this yaml file to raed metadata; {}".format(e.args[0]))

                if self.metadata is not None and isinstance(self.metadata, dict):
                    self.dependency["roles"] = self.metadata.get("dependencies", [])
                    self.dependency["collections"] = self.metadata.get("collections", [])
        
        requirements_yml_path = os.path.join(fullpath, "requirements.yml")
        if os.path.exists(requirements_yml_path):
            with open(requirements_yml_path, "r") as file:
                try:
                    self.requirements = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load requirements.yml; {}".format(e.args[0]))

        parts = tasks_dir_path.split("/")
        if len(parts) < 2:
            raise ValueError("role path is wrong")
        role_name = parts[-2]
        self.name = role_name
        defined_in = fullpath
        if basedir != "":
            if defined_in.startswith(basedir):
                defined_in = defined_in[len(basedir):]
                if defined_in.startswith("/"):
                    defined_in = defined_in[1:]
        self.defined_in = defined_in
        collection = ""
        fqcn = role_name
        if collection_name != "":
            collection = collection_name
            fqcn = "{}.{}".format(collection_name, role_name)
        self.collection = collection
        self.fqcn = fqcn
        self.set_key()

        if os.path.exists(os.path.join(fullpath, "playbooks")):
            playbook_files = safe_glob(fullpath + "/playbooks/**/*.yml", recursive=True)
            playbooks = []
            for f in playbook_files:
                p = Playbook()
                try:
                    p.load(f, role_name=role_name, collection_name=collection_name, basedir=basedir)
                except PlaybookFormatError as e:
                        logging.warning("this file is not in a playbook format, maybe not a playbook file: {}".format(e.args[0]))
                        continue
                except:
                    logging.exception("error while loading the playbook at {}".format(f))
                if load_children:
                    playbooks.append(p)
                else:
                    playbooks.append(p.defined_in)
            if not load_children:
                playbooks = sorted(playbooks)
            self.playbooks = playbooks

        if os.path.exists(defaults_dir_path):
            patterns = [
                defaults_dir_path + "/**/*.yml",
                defaults_dir_path + "/**/*.yaml"
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
                        logging.error("failed to load this yaml file to raed default variables; {}".format(e.args[0]))
            self.default_variables = default_variables

        if not os.path.exists(tasks_dir_path):
            # a role possibly has no tasks
            return

        modules = []
        module_files = search_module_files(fullpath, module_dir_paths)
        for module_file_path in module_files:
            m = Module()
            try:
                m.load(module_file_path, collection_name=collection_name, role_name=fqcn, basedir=basedir)
            except:
                logging.exception("error while loading the module at {}".format(module_file_path))
            if load_children:
                modules.append(m)
            else:
                modules.append(m.defined_in)
        if not load_children:
            modules = sorted(modules)
        self.modules = modules

        patterns = [
            tasks_dir_path + "/**/*.yml",
            tasks_dir_path + "/**/*.yaml"
        ]
        # ansible.network collection has this type of another taskfile directory
        if os.path.exists(includes_dir_path):
            patterns.extend(
                [
                    includes_dir_path + "/**/*.yml",
                    includes_dir_path + "/**/*.yaml"
                ]
            )
        task_yaml_files = safe_glob(patterns, recursive=True)

        taskfiles = []
        for task_yaml_path in task_yaml_files:
            tf = TaskFile()
            try:
                tf.load(task_yaml_path, role_name=fqcn, collection_name=collection_name, basedir=basedir)
            except:
                logging.exception("error while loading the task file at {}".format(task_yaml_path))
            if load_children:
                taskfiles.append(tf)
            else:
                taskfiles.append(tf.defined_in)
        if not load_children:
            taskfiles = sorted(taskfiles)
        self.taskfiles = taskfiles

    def set_key(self):
        global_key_prefix = make_global_key_prefix(self.collection, "")
        global_key = "{}{}{}{}".format(global_key_prefix, type(self).__name__.lower(), key_delimiter, self.fqcn.lower())
        local_key = "{}{}{}".format(type(self).__name__.lower(), key_delimiter, self.defined_in.lower())
        self.key = global_key
        self.local_key = local_key

    def children_to_key(self):
        module_keys = [m.key if isinstance(m, Module) else m  for m in self.modules]
        self.modules = module_keys

        playbook_keys = [p.key if isinstance(p, Playbook) else p for p in self.playbooks]
        self.playbooks = playbook_keys

        taskfile_keys = [tf.key if isinstance(tf, TaskFile) else tf for tf in self.taskfiles]
        self.taskfiles = taskfile_keys

    @property
    def resolver_targets(self):
        return self.taskfiles + self.modules

@dataclass
class RoleInPlay(JSONSerializable, Resolvable):
    name: str = ""
    options: dict = field(default_factory=dict)
    defined_in: str = ""
    role_index: int = -1
    play_index: int = -1

    role: str = ""
    collection: str = ""
    
    resolved_name: str = "" # resolved later
    possible_candidates: list = field(default_factory=list) # candidates of resovled_name

    annotations: dict = field(default_factory=dict)
    collections_in_play: list = field(default_factory=list)

    def load(self, name, options, defined_in, role_index, play_index, role_name="", collection_name="", collections_in_play=[], basedir=""):
        if name == "":
            if "name" in options:
                name = options["name"]
                options.pop("name", None)
        self.name = name
        self.options = options
        if basedir != "":
            if defined_in.startswith(basedir):
                defined_in = defined_in[len(basedir):]
                if defined_in.startswith("/"):
                    defined_in = defined_in[1:]
        self.defined_in = defined_in
        self.role = role_name
        self.collection = collection_name
        self.role_index = role_index
        self.play_index = play_index
        self.collections_in_play = collections_in_play

    @property
    def resolver_targets(self):
        return None

@dataclass
class Play(JSONSerializable, Resolvable):
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
    roles: list = field(default_factory=list)   # not actual Role, but RoleInPlay defined in this playbook
    options: dict = field(default_factory=dict)
    collections_in_play: list = field(default_factory=list)
    variables: dict = field(default_factory=dict)

    def load(self, path, index, play_block_dict, role_name="", collection_name="", parent_key="", parent_local_key="", basedir=""):
        if play_block_dict is None:
            raise ValueError("play block dict is required to load Play")
        if not isinstance(play_block_dict, dict):
            raise PlaybookFormatError("this play block is not loaded as dict; maybe this is not a playbook")
        data_block = play_block_dict
        if "hosts" not in data_block and "import_playbook" not in data_block and "include" not in data_block:
            raise PlaybookFormatError("this play block does not have \"hosts\", \"import_playbook\" and \"include\"; maybe this is not a playbook")
        
        self.index = index
        self.role = role_name
        self.collection = collection_name
        self.set_key(parent_key, parent_local_key)
        
        play_name = data_block.get("name", "")
        collections_in_play = data_block.get("collections", [])
        pre_tasks = []
        post_tasks = []
        tasks = []
        roles = []
        play_options = {}
        import_module = ""
        import_playbook = ""
        __pre_task_blocks = get_task_blocks(task_dict_list=data_block.get("pre_tasks", []))
        __task_blocks = get_task_blocks(task_dict_list=data_block.get("tasks", []))
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
                    t = Task()
                    try:
                        t.load(path=path, index=i, task_block_dict=task_dict, role_name=role_name, collection_name=collection_name, collections_in_play=collections_in_play, play_index=index, parent_key=self.key, parent_local_key=self.local_key, basedir=basedir)
                    except TaskFormatError:
                        logging.warning("this task is wrong format; skip the task in {}, index: {}".format(path, i))
                        continue
                    except:
                        logging.exception("error while loading the task at {} (index={})".format(path, i))
                    pre_tasks.append(t)
            elif k == "tasks":
                if not isinstance(v, list):
                    continue
                task_blocks = get_task_blocks(task_dict_list=v)
                if task_blocks is None:
                    continue
                for i, task_dict in enumerate(task_blocks):
                    _i = i + pre_task_num
                    t = Task()
                    try:
                        t.load(path=path, index=_i, task_block_dict=task_dict, role_name=role_name, collection_name=collection_name, collections_in_play=collections_in_play, play_index=index, parent_key=self.key, parent_local_key=self.local_key, basedir=basedir)
                    except TaskFormatError:
                        logging.warning("this task is wrong format; skip the task in {}, index: {}".format(path, i))
                        continue
                    except:
                        logging.exception("error while loading the task at {} (index={})".format(path, i))
                    tasks.append(t)
            elif k == "post_tasks":
                if not isinstance(v, list):
                    continue
                task_blocks = get_task_blocks(task_dict_list=v)
                if task_blocks is None:
                    continue
                for i, task_dict in enumerate(task_blocks):
                    _i = i + pre_task_num + task_num
                    t = Task()
                    try:
                        t.load(path=path, index=_i, task_block_dict=task_dict, role_name=role_name, collection_name=collection_name, collections_in_play=collections_in_play, play_index=index, parent_key=self.key, parent_local_key=self.local_key, basedir=basedir)
                    except TaskFormatError:
                        logging.warning("this task is wrong format; skip the task in {}, index: {}".format(path, i))
                        continue
                    except:
                        logging.exception("error while loading the task at {} (index={})".format(path, i))
                    post_tasks.append(t)
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
                    rip = RoleInPlay()
                    try:
                        rip.load(name=r_name, options=role_options, defined_in=path, role_index=i, play_index=index, role_name=role_name, collection_name=collection_name, collections_in_play=collections_in_play, basedir=basedir)
                    except:
                        logging.exception("error while loading the role in playbook at {} (play_index={}, role_index={})".format(path, i, j))
                    roles.append(rip)
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

        self.name = play_name
        self.defined_in = path
        self.import_module = import_module
        self.import_playbook = import_playbook
        self.pre_tasks = pre_tasks
        self.tasks = tasks
        self.post_tasks = post_tasks
        self.roles = roles
        self.options = play_options
        self.collections_in_play = collections_in_play
        

    def set_key(self, parent_key="", parent_local_key=""):
        index_info = "[{}]".format(self.index)
        global_key = "{}{}{}{}{}".format(parent_key, object_delimiter, type(self).__name__.lower(), key_delimiter, index_info)
        local_key = "{}{}{}{}{}".format(parent_local_key, object_delimiter, type(self).__name__.lower(), key_delimiter, index_info)
        self.key = global_key
        self.local_key = local_key

    def children_to_key(self):
        pre_task_keys = [t.key if isinstance(t, Task) else t for t in self.pre_tasks]
        self.pre_tasks = pre_task_keys

        task_keys = [t.key if isinstance(t, Task) else t for t in self.tasks]
        self.tasks = task_keys

        post_task_keys = [t.key if isinstance(t, Task) else t for t in self.post_tasks]
        self.post_tasks = post_task_keys

    @property
    def id(self):
        return json.dumps({"path":self.defined_in, "index": self.index})

    @property
    def resolver_targets(self):
        return self.pre_tasks + self.tasks + self.roles
        

@dataclass
class Playbook(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    key: str = ""
    local_key: str = ""

    role: str = ""
    collection: str = ""
    
    plays: list = field(default_factory=list)

    used_in: list = field(default_factory=list) # resolved later

    annotations: dict = field(default_factory=dict)

    variables: dict = field(default_factory=dict)
    options: dict = field(default_factory=dict)

    def load(self, path, role_name="", collection_name="", basedir=""):
        fullpath = ""
        if os.path.exists(path):
            fullpath = path
        if os.path.exists(os.path.join(basedir, path)):
            fullpath = os.path.join(basedir, path)
        if fullpath == "":
            raise ValueError("file not found")
        defined_in = fullpath
        if basedir != "":
            if defined_in.startswith(basedir):
                defined_in = defined_in[len(basedir):]
                if defined_in.startswith("/"):
                    defined_in = defined_in[1:]
        self.defined_in = defined_in
        self.name = os.path.basename(fullpath)
        self.role = role_name
        self.collection = collection_name
        self.set_key()
        data = None
        if fullpath != "":
            with open(fullpath , "r") as file:
                try:
                    data = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load this yaml file to load playbook; {}".format(e.args[0]))
        if data is None:
            return
        if not isinstance(data, list):
            raise PlaybookFormatError("playbook must be loaded as a list, but got {}".format(type(data).__name__))

        plays = []
        for i, play_dict in enumerate(data):
            play = Play()
            try:
                play.load(path=defined_in, index=i, play_block_dict=play_dict, role_name=role_name, collection_name=collection_name, parent_key=self.key, parent_local_key=self.local_key, basedir=basedir)
            except PlaybookFormatError:
                logging.warning("this play is wrong format; skip the play in {}, index: {}".format(fullpath, i))
                continue
            except:
                logging.exception("error while loading the play at {} (index={})".format(fullpath, i))
            plays.append(play)
        self.plays = plays

    def set_key(self):
        global_key_prefix = make_global_key_prefix(self.collection, self.role)
        global_key = "{}{}{}{}".format(global_key_prefix, type(self).__name__.lower(), key_delimiter, self.defined_in.lower())
        local_key = "{}{}{}".format(type(self).__name__.lower(), key_delimiter, self.defined_in.lower())
        self.key = global_key
        self.local_key = local_key

    def children_to_key(self):
        play_keys = [play.key if isinstance(play, Play) else play for play in self.plays]
        self.plays = play_keys

    @property
    def resolver_targets(self):
        if "plays" in self.__dict__:
            return self.plays
        else:
            return self.roles + self.tasks
        
@dataclass
class Repository(JSONSerializable, Resolvable):
    name: str = ""
    path: str = ""

    my_collection_name: str = ""    # if set, this repository is a collection repository
    
    playbooks: list = field(default_factory=list)
    roles: list = field(default_factory=list)

    requirements: dict = field(default_factory=dict)

    installed_collections_path: str = ""
    installed_collections: list = field(default_factory=list)

    installed_roles_path: str = ""
    installed_roles: list = field(default_factory=list)
    
    modules: list = field(default_factory=list)
    taskfiles: list = field(default_factory=list)
    version: str = ""

    annotations: dict = field(default_factory=dict)

    def load(self, path="", installed_collections_path="", installed_roles_path="", my_collection_name="", basedir="", load_children=True):
        repo_path = ""
        if path == "":
            # if path is empty, just load installed collections / roles
            repo_path = "" 
        else:
            # otherwise, find the root path by searching playbooks
            repo_path = self.find_best_root_path(path)
            if repo_path == "":
                repo_path = path
                logging.warning("failed to find a root directory for ansible files; use \"{}\" but this may be wrong".format(path))

        if repo_path != "":
            if my_collection_name == "":
                my_collection_name = self.find_my_collection_name(repo_path)
            if my_collection_name != "":
                self.my_collection_name = my_collection_name

        if basedir == "":
            basedir = path

        logging.info("start loading the repo {}".format(repo_path))
        logging.debug("start loading playbooks")
        self.load_playbooks(repo_path, basedir=basedir, load_children=load_children)
        logging.debug("done ... {} playbooks loaded".format(len(self.playbooks)))
        logging.debug("start loading roles")
        self.load_roles(repo_path, basedir=basedir, load_children=load_children)
        logging.debug("done ... {} roles loaded".format(len(self.roles)))
        logging.debug("start loading modules (that are defined in this repository)")
        self.load_modules(repo_path, basedir=basedir, load_children=load_children)
        logging.debug("done ... {} modules loaded".format(len(self.modules)))
        logging.debug("start loading taskfiles (that are defined for playbooks in this repository)")
        self.load_taskfiles(repo_path, basedir=basedir, load_children=load_children)
        logging.debug("done ... {} task files loaded".format(len(self.taskfiles)))
        logging.debug("start loading installed collections")
        self.load_installed_collections(installed_collections_path)
        logging.debug("done ... {} collections loaded".format(len(self.installed_collections)))
        logging.debug("start loading installed roles")
        self.load_installed_roles(installed_roles_path)
        logging.debug("done ... {} roles loaded".format(len(self.installed_roles)))
        self.load_requirements(path=repo_path)
        self.path = repo_path
        self.installed_collections_path = installed_collections_path
        self.installed_roles_path = installed_roles_path
        logging.info("done")

    def load_playbooks(self, path, basedir="", load_children=True):
        if path == "":
            return
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
                p = Playbook()
                try:
                    p.load(fpath, basedir=basedir)
                except PlaybookFormatError as e:
                    logging.warning("this file is not in a playbook format, maybe not a playbook file: {}".format(e.args[0]))
                    continue
                except:
                    logging.exception("error while loading the playbook at {}".format(fpath))
                if load_children:
                    playbooks.append(p)
                else:
                    playbooks.append(p.defined_in)
        if not load_children:
            playbooks = sorted(playbooks)
        self.playbooks = playbooks

    def load_roles(self, path, basedir="", load_children=True):
        if path == "":
            return
        roles_patterns = ["roles", "playbooks/roles", "playbook/roles"]
        roles_dir_path = ""
        for r_p in roles_patterns:
            candidate = os.path.join(path, r_p)
            if os.path.exists(candidate):
                roles_dir_path = candidate
                break
        if roles_dir_path == "":
            return
        dirs = os.listdir(roles_dir_path)
        roles = []
        for dir_name in dirs:
            role_dir = os.path.join(roles_dir_path, dir_name)
            r = Role()
            try:
                r.load(role_dir, basedir=basedir)
            except:
                logging.exception("error while loading the role at {}".format(role_dir))
            if load_children:
                roles.append(r)
            else:
                roles.append(r.defined_in)
        if not load_children:
            roles = sorted(roles)
        self.roles = roles

    def load_requirements(self, path):
        requirements_yml_path = os.path.join(path, "requirements.yml")
        if os.path.exists(requirements_yml_path):
            with open(requirements_yml_path, "r") as file:
                try:
                    self.requirements = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load requirements.yml; {}".format(e.args[0]))

    def load_installed_collections(self, installed_collections_path):
        search_path = installed_collections_path
        if installed_collections_path == "" or not os.path.exists(search_path):
            return
        if os.path.exists(os.path.join(search_path, "ansible_collections")):
            search_path = os.path.join(search_path, "ansible_collections")
        dirs = os.listdir(search_path)
        collections = []
        basedir = os.path.dirname(os.path.normpath(installed_collections_path))
        for d in dirs:
            if collection_info_dir_re.match(d):
                continue
            if not os.path.exists(os.path.join(search_path, d)):
                continue
            subdirs = os.listdir(os.path.join(search_path, d))
            for sd in subdirs:
                collection_path = os.path.join(search_path, d, sd)
                c = Collection()
                try:
                    c.load(collection_dir=collection_path, basedir=basedir)
                except:
                    logging.exception("error while loading the collection at {}".format(collection_path))
                collections.append(c)
        self.installed_collections = collections

    def load_installed_roles(self, installed_roles_path):
        search_path = installed_roles_path
        if installed_roles_path == "" or not os.path.exists(search_path):
            return
        dirs = os.listdir(search_path)
        roles = []
        basedir = os.path.dirname(os.path.normpath(installed_roles_path))
        for d in dirs:
            role_path = os.path.join(installed_roles_path, d)
            role_meta_files = safe_glob(role_path + "/**/meta/main.yml", recursive=True)

            roles_root_dirs = set([f.split("/roles/")[-2] for f in role_meta_files if "/roles/" in f])
            module_dirs = []
            for roles_root_dir in roles_root_dirs:
                for module_dir_pattern in module_dir_patterns:
                    moddir = os.path.join(roles_root_dir, module_dir_pattern)
                    if os.path.exists(moddir):
                        module_dirs.append(moddir)

            for i, role_meta_file in enumerate(role_meta_files):
                role_dir_path = role_meta_file.replace("/meta/main.yml", "")
                module_dir_paths = []
                if i == 0:
                    module_dir_paths = module_dirs
                r = Role()
                try:
                    r.load(role_dir_path, module_dir_paths=module_dir_paths, basedir=basedir)
                except:
                    logging.exception("error while loading the role at {}".format(role_dir_path))
                roles.append(r)
        self.installed_roles = roles

    # modules defined in a SCM repo should be in `library` directory in the best practice case
    # https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html
    # however, it is often defined in `plugins/modules` directory in a collection repository,
    # so we search both the directories
    def load_modules(self, path, basedir="", load_children=True):
        if path == "":
            return
        if not os.path.exists(path):
            return
        
        module_files = search_module_files(path)
        if len(module_files) > 0:
            modules = []
            for module_file_path in module_files:
                m = Module()
                try:
                    m.load(module_file_path, collection_name=self.my_collection_name, basedir=basedir)
                except:
                    logging.exception("error while loading the module at {}".format(module_file_path))
                if load_children:
                    modules.append(m)
                else:
                    modules.append(m.defined_in)
            if not load_children:
                modules = sorted(modules)
            self.modules = modules

    # playbooks possibly include/import task files around the playbook file
    # we search this type of isolated taskfile (means not in a role) in `playbooks` and `tasks` dir
    def load_taskfiles(self, path, basedir="", load_children=True):
        if not os.path.exists(path):
            return
        
        taskfile_paths = search_taskfiles_for_playbooks(path)
        if len(taskfile_paths) > 0:
            taskfiles = []
            for taskfile_path in taskfile_paths:
                tf = TaskFile()
                try:
                    tf.load(taskfile_path, basedir=basedir)
                except:
                    logging.exception("error while loading the task file at {}".format(taskfile_path))
                if load_children:
                    taskfiles.append(tf)
                else:
                    taskfiles.append(tf.defined_in)
            if not load_children:
                taskfiles = sorted(taskfiles)
            self.taskfiles = taskfiles

    def find_my_collection_name(self, path):
        found_galaxy_ymls = safe_glob(path + "/**/galaxy.yml", recursive=True)
        my_collection_name = ""
        if len(found_galaxy_ymls) > 0:
            galaxy_yml = found_galaxy_ymls[0]
            my_collection_info = None
            with open(galaxy_yml, "r") as file:
                try:
                    my_collection_info = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load this yaml file to read galaxy.yml; {}".format(e.args[0]))
            if my_collection_info is None:
                return ""
            namespace = my_collection_info.get("namespace", "")
            name = my_collection_info.get("name", "")
            my_collection_name = "{}.{}".format(namespace, name)
        return my_collection_name

    
    def find_best_root_path(self, path):
        # get all possible playbooks
        playbooks = search_playbooks(path)
        # sort by directory depth to find the most top playbook
        playbooks = sorted(playbooks, key=lambda x: len(x.split(os.sep)))
        # still "repo/xxxxx/sample1.yml" may come before "repo/playbooks/sample2.yml" because the depth are same,
        # so specifically put "playbooks" or "playbook" ones on top of the list
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

    @property
    def resolver_targets(self):
        return self.playbooks + self.roles + self.modules + self.installed_roles + self.installed_collections


def get_object(json_path, type, name, cache={}):
    json_type = ""
    json_str = ""
    cached = cache.get(json_path, None)
    if cached is None:
        if not os.path.exists(json_path):
            raise ValueError("the json path \"{}\" not found".format(json_path))
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


# inherit Repository for convenience, but this is not a Repository but one or multiple Role / Collection
@dataclass
class GalacyArtifact(Repository):
    type: str = "" # Role or Collection
    
    module_dict: dict = field(default_factory=dict) # make it easier to search a module
    task_dict: dict = field(default_factory=dict) # make it easier to search a task
    taskfile_dict: dict = field(default_factory=dict) # make it easier to search a taskfile
    role_dict: dict = field(default_factory=dict) # make it easier to search a role
    playbook_dict: dict = field(default_factory=dict) # make it easier to search a playbook
    collection_dict: dict = field(default_factory=dict) # make it easier to search a collection
    

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
                    file_list.append(os.path.join(dirpath, file))
    return file_list
    
def search_taskfiles_for_playbooks(path, taskfile_dir_paths=[]):
    file_list = []
    # must copy the input here; otherwise, the added items are kept forever
    search_targets = [p for p in taskfile_dir_paths]
    for playbook_taskfile_dir_pattern in playbook_taskfile_dir_patterns:
        search_targets.append(os.path.join(path, playbook_taskfile_dir_pattern))
    candidates = []
    for search_target in search_targets:
        patterns = [
            search_target + "/**/*.yml",
            search_target + "/**/*.yaml"
        ]
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
                    d = yaml.safe_load(file)
                except Exception as e:
                    logging.error("failed to load this yaml file to search task files; {}".format(e.args[0]))
            # if d cannot be loaded as tasks yaml file, skip it
            if d is None or not isinstance(d, list):
                continue
            candidates.append(f)
    return candidates

# this method is based on awx code https://github.com/ansible/awx/blob/devel/awx/main/utils/ansible.py#L42-L64
def could_be_playbook(fpath):
    basename, ext = os.path.splitext(fpath)
    if ext not in [".yml", ".yaml"]:
        return False
    # Filter files that do not have either hosts or top-level
    # includes. Use regex to allow files with invalid YAML to
    # show up.
    matched = False
    try:
        with codecs.open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
            for n, line in enumerate(f):
                if valid_playbook_re.match(line):
                    matched = True
                    break
                # Any YAML file can also be encrypted with vault;
                # allow these to be used as the main playbook.
                elif n == 0 and line.startswith('$ANSIBLE_VAULT;'):
                    matched = True
                    break
    except IOError:
        return False
    return matched

# this method is based on awx code https://github.com/ansible/awx/blob/devel/awx/main/models/projects.py#L206-L217
def search_playbooks(root_path):
    results = []
    if root_path and os.path.exists(root_path):
        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
            if skip_directory(dirpath):
                continue
            for filename in filenames:
                fpath = os.path.join(dirpath, filename)
                if could_be_playbook(fpath):
                    results.append(fpath)
    return sorted(results, key=lambda x: x.lower())

# this method is based on awx code https://github.com/ansible/awx/blob/devel/awx/main/utils/ansible.py#L24-L39
def skip_directory(relative_directory_path):
    path_elements = relative_directory_path.split(os.sep)
    # Exclude files in a roles subdirectory.
    if 'roles' in path_elements:
        return True
    # Filter files in a tasks subdirectory.
    if 'tasks' in path_elements:
        return True
    for element in path_elements:
        # Do not include dot files or dirs
        if element.startswith('.'):
            return True
    # Exclude anything inside of group or host vars directories
    if 'group_vars' in path_elements or 'host_vars' in path_elements:
        return True
    return False