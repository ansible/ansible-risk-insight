from dataclasses import dataclass, field
from unicodedata import category
import io
import re
import os
import codecs
from urllib.robotparser import RobotFileParser
import yaml
import glob
import json
import jsonpickle
import logging


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


valid_playbook_re = re.compile(r'^\s*?-?\s*?(?:hosts|include|import_playbook):\s*?.*?$')
module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')
collection_info_dir_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+-[0-9]+\.[0-9]+\.[0-9]\.info$')

module_dir_patterns = [
    "library",
    "plugins/modules",
    "plugins/actions",
]

playbook_taskfile_dir_patterns = [
    "tasks",
    "playbooks"
]

class PlaybookFormatError(Exception):
    pass

class TaskFileFormatError(Exception):
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
            t.resolve(resolver)

        # apply resolver again here because some attributes was not set at first
        resolver.apply(self)
        return

    @property
    def resolver_targets(self):
        raise NotImplementedError

@dataclass
class Module(JSONSerializable, Resolvable):
    name: str = ""
    fqcn: str = ""
    collection: str = ""
    role: str = ""
    defined_in: str = ""
    builtin: bool = False
    used_in: list = field(default_factory=list) # resolved later

    annotations: dict = field(default_factory=dict)

    def load(self, module_file_path, collection_name="", role_name=""):
        if module_file_path == "":
            raise ValueError("require module file path to load a Module")
        file_name = os.path.basename(module_file_path)
        module_name = file_name.replace(".py", "")
        self.name = module_name
        if collection_name != "":
            self.collection = collection_name
            self.fqcn = "{}.{}".format(collection_name, module_name)
        if role_name != "":
            self.role = role_name
            self.fqcn = module_name # if module is defined in a role, it does not have fqcn and just called in the role
        self.defined_in = module_file_path

    @property
    def resolver_targets(self):
        return None
@dataclass
class Collection(JSONSerializable, Resolvable):
    name: str = ""
    path: str = ""
    metadata: dict = field(default_factory=dict)
    playbooks: list = field(default_factory=list)
    roles: list = field(default_factory=list)
    modules: list = field(default_factory=list)

    annotations: dict = field(default_factory=dict)

    def load(self, collection_dir):
        if not os.path.exists(collection_dir):
            raise ValueError("directory not found")
        parts = collection_dir.split("/")
        if len(parts) < 2:
            raise ValueError("collection directory path is wrong")
        collection_name = "{}.{}".format(parts[-2], parts[-1])

        manifest_file_path = os.path.join(collection_dir, "MANIFEST.json")
        if os.path.exists(manifest_file_path):
            with open(manifest_file_path, "r") as file:
                self.metadata = json.load(file)
        
        playbook_files = glob.glob(collection_dir + "/playbooks/**/*.yml", recursive=True)
        playbooks = []
        for f in playbook_files:
            p = Playbook()
            try:
                p.load(f)
            except:
                logging.exception("error while loading the playbook at {}".format(f))
            playbooks.append(p)

        role_tasks_files = glob.glob(collection_dir + "/roles/*/tasks/main.yml", recursive=True)
        roles = []
        for f in role_tasks_files:
            role_dir_path = f.replace("/tasks/main.yml", "")
            r = Role()
            try:
                r.load(role_dir_path, collection_name=collection_name)
            except:
                logging.exception("error while loading the role at {}".format(f))
            roles.append(r)

        module_files = search_module_files(collection_dir)
        modules = []
        for f in module_files:
            m = Module()
            try:
                m.load(f, collection_name=collection_name)
            except:
                logging.exception("error while loading the module at {}".format(f))
            modules.append(m)
        self.name = collection_name
        self.path = collection_dir
        self.playbooks = playbooks
        self.roles = roles
        self.modules = modules

    @property
    def resolver_targets(self):
        return self.playbooks + self.roles + self.modules

@dataclass
class Task(JSONSerializable, Resolvable):
    name: str = ""
    module: str = ""    
    index: int = -1
    defined_in: str = ""
    options: dict = field(default_factory=dict)
    module_options: dict = field(default_factory=dict)
    executable: str = ""
    executable_type: str = ""
    resolved_name: str = ""  # FQCN for Module and Role. Or a file path for TaskFile.  resolved later
    possible_candidates: list = field(default_factory=list) # candidates of resovled_name

    annotations: dict = field(default_factory=dict)

    def load(self, path, index, task_block_dict):
        if not os.path.exists(path):
            raise ValueError("file not found")
        if not path.endswith(".yml") and not path.endswith(".yaml"):
            raise ValueError("task yaml file must be \".yml\" or \".yaml\"")
        if task_block_dict is None:
            raise ValueError("task block dict is required to load Task")
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
        executable = module_name
        executable_type = "Module"
        if module_short_name in ["import_role", "include_role"]:
            executable = module_options["name"]
            executable_type = "Role"
        if module_short_name in ["import_tasks", "include_tasks"]:
            taskfile_ref = ""
            if isinstance(module_options, str):
                taskfile_ref = module_options
                # include/import tasks can have variable as task file name like below
                # we keep this as is and this cannot be resolved.
                #
                # tasks:
                #   - include_tasks: {{ target_task_file_path }}
                # 
                # Also, include/import tasks can have a string module option like below
                # in this case, we parse it correctly.
                # 
                # tasks:
                #   - include_tasks: sample.yml tags=tag1
                #
                if "{{" not in taskfile_ref and " " in taskfile_ref:
                    parts = [p for p in taskfile_ref.split(" ") if p != ""]
                    taskfile_ref = parts[0]
                    module_options = {}
                    for p in parts[1:]:
                        opt_parts = p.split("=")
                        key = opt_parts[0]
                        val = "" if len(opt_parts) == 1 else opt_parts[1]
                        module_options[key] = val
            elif isinstance(module_options, dict):
                taskfile_ref = module_options["file"]
            executable = taskfile_ref
            executable_type = "TaskFile"

        self.name = task_name
        self.options = task_options
        self.module = module_name
        self.module_options = module_options
        self.defined_in = path 
        self.index = index
        self.executable = executable
        self.executable_type = executable_type

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

    @property
    def id(self):
        return json.dumps({"path":self.defined_in, "index": self.index})

    @property
    def resolver_targets(self):
        return None

@dataclass
class TaskFile(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    tasks: list = field(default_factory=list)
    role: str = ""  # role name of this task file; this might be empty because a task file can be defined out of roles

    used_in: list = field(default_factory=list) # resolved later

    annotations: dict = field(default_factory=dict)

    def load(self, path, role_name=""):
        if not os.path.exists(path):
            raise ValueError("file not found")
        if not path.endswith(".yml") and not path.endswith(".yaml"):
            raise ValueError("task yaml file must be \".yml\" or \".yaml\"")
        self.name = os.path.basename(path)
        self.defined_in = path
        if role_name != "":
            self.role = role_name
        task_dicts = self.get_task_blocks(path)
        if task_dicts is None:
            return
        tasks = []
        for i, t_dict in enumerate(task_dicts):
            t = Task()
            try:
                t.load(path, i, t_dict)
            except:
                logging.exception("error while loading the task file at {}".format(path))
            tasks.append(t)
        self.tasks = tasks

    def get_task_blocks(self, fpath):
        d = None
        if fpath == "":
            return None
        else:
            if not os.path.exists(fpath):
                return None
            with open(fpath , "r") as file:
                d = yaml.safe_load(file)
        if d is None:
            return None
        tasks = []
        for task_dict in d:
            task_dict_loop = self.flatten_block_tasks(task_dict)
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
    def flatten_block_tasks(self, task_dict):
        tasks = []
        if "block" in task_dict:
            tasks_in_block = task_dict.get("block", [])
            for t_dict in tasks_in_block:
                tasks_in_item = self.flatten_block_tasks(t_dict)
                tasks.extend(tasks_in_item)
        else:
            tasks = [task_dict]
        return tasks

    @property
    def resolver_targets(self):
        return self.tasks

@dataclass
class Role(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    fqcn: str = ""
    metadata: dict = field(default_factory=dict)
    collection: str = ""
    taskfiles: list = field(default_factory=list)     # 1 role can have multiple task yamls
    modules: list = field(default_factory=list)     # roles/xxxx/library/zzzz.py can be called as module zzzz

    source: str = "" # collection/scm repo/galaxy

    annotations: dict = field(default_factory=dict)

    def load(self, path, collection_name="", module_dir_paths=[]):
        if not os.path.exists(path):
            raise ValueError("directory not found")
        meta_file_path = ""
        tasks_dir_path = ""
        if path != "":
            meta_file_path = os.path.join(path, "meta/main.yml")
            tasks_dir_path = os.path.join(path, "tasks")
        
        if os.path.exists(meta_file_path):
            with open(meta_file_path, "r") as file:
                self.metadata = yaml.safe_load(file)

        parts = tasks_dir_path.split("/")
        if len(parts) < 2:
            raise ValueError("role path is wrong")
        role_name = parts[-2]
        self.name = role_name
        self.defined_in = path
        collection = ""
        fqcn = role_name
        if collection_name != "":
            collection = collection_name
            fqcn = "{}.{}".format(collection_name, role_name)
        self.collection = collection
        self.fqcn = fqcn
        if not os.path.exists(tasks_dir_path):
            # a role possibly has no tasks
            return

        modules = []
        module_files = search_module_files(path, module_dir_paths)
        for module_file_path in module_files:
            m = Module()
            try:
                m.load(module_file_path, role_name=role_name)
            except:
                logging.exception("error while loading the module at {}".format(module_file_path))
            modules.append(m)
        self.modules = modules

        task_yaml_files = []
        task_yaml_files += glob.glob(tasks_dir_path + "/**/*.yml", recursive=True)
        task_yaml_files += glob.glob(tasks_dir_path + "/**/*.yaml", recursive=True)
        
        taskfiles = []
        for task_yaml_path in task_yaml_files:
            tf = TaskFile()
            try:
                tf.load(task_yaml_path, role_name=role_name)
            except:
                logging.exception("error while loading the task file at {}".format(task_yaml_path))
            taskfiles.append(tf)
        self.taskfiles = taskfiles

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
    
    resolved_name: str = "" # resolved later
    possible_candidates: list = field(default_factory=list) # candidates of resovled_name

    annotations: dict = field(default_factory=dict)

    def load(self, name, options, defined_in, role_index, play_index):
        if name == "":
            if "name" in options:
                name = options["name"]
                options.pop("name", None)
        self.name = name
        self.options = options
        self.defined_in = defined_in
        self.role_index = role_index
        self.play_index = play_index

    @property
    def resolver_targets(self):
        return None

@dataclass
class Playbook(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    
    tasks: list = field(default_factory=list)
    roles: list = field(default_factory=list)   # not actual Role, but RoleInPlay defined in this playbook
    import_playbooks: list = field(default_factory=list) # list of playbook paths that are imported in this playbook

    source: str = "" # collection/scm repo
    used_in: list = field(default_factory=list) # resolved later

    annotations: dict = field(default_factory=dict)

    def load(self, path):
        if not os.path.exists(path):
            raise ValueError("file not found")
        self.defined_in = path
        self.name = os.path.basename(path)
        data = None
        if path != "":
            with open(path , "r") as file:
                data = yaml.safe_load(file)
        if data is None:
            return
        if not isinstance(data, list):
            raise PlaybookFormatError("playbook must be loaded as a list, but got {}".format(type(data).__name__))

        roles = []
        import_playbooks = []
        for i, play_dict in enumerate(data):
            if "roles" in play_dict:
                for j, r_block in enumerate(play_dict.get("roles", [])):
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
                        rip.load(name=r_name, options=role_options, defined_in=path, role_index=j, play_index=i)
                    except:
                        logging.exception("error while loading the role in playbook at {} (play_index={}, role_index={})".format(path, i, j))
                    roles.append(rip)
            if "import_playbook" in play_dict:
                playbook_dir = os.path.dirname(self.defined_in)
                playbook_path = os.path.join(playbook_dir, play_dict["import_playbook"])
                import_playbooks.append(playbook_path)
        tasks = []
        loaded_tasks = self.get_task_blocks(self.defined_in)
        for index, t_block in enumerate(loaded_tasks):
            t = Task()
            try:
                t.load(path=self.defined_in, index=index, task_block_dict=t_block)
            except:
                logging.exception("error while loading the task at {} (index={})".format(self.defined_in, index))
            tasks.append(t)

        self.tasks = tasks
        self.roles = roles
        self.import_playbooks = import_playbooks

    def get_task_blocks(self, fpath):
        d = None
        if fpath == "":
            return None
        else:
            if not os.path.exists(fpath):
                return None
            with open(fpath , "r") as file:
                d = yaml.safe_load(file)
        if d is None:
            return None
        tasks = []
        for play_dict in d:
            tmp_tasks = play_dict.get("tasks", [])
            tmp_pre_tasks = play_dict.get("pre_tasks", [])
            # tasks/pre_tasks might be None for a playbook like below (`pre_tasks` is defined but null)
            # so replace them with empty array in the case
            # 
            # hosts: localhost
            # pre_tasks:
            # roles: 
            #   - role: sample_role
            if tmp_tasks is None:
                tmp_tasks = []
            if tmp_pre_tasks is None:
                tmp_pre_tasks = []
            if len(tmp_tasks) + len(tmp_pre_tasks) == 0:
                continue
            tasks_in_play = []
            for task_dict in tmp_tasks:
                task_dict_loop = [task_dict]
                if "block" in task_dict:    # tasks defined in a "block" are flattened
                    task_dict_loop = task_dict.get("block", [])
                tasks_in_play.extend(task_dict_loop)
            for task_dict in tmp_pre_tasks:
                task_dict_loop = [task_dict]
                if "block" in task_dict:    # tasks defined in a "block" are flattened
                    task_dict_loop = task_dict.get("block", [])
                tasks_in_play.extend(task_dict_loop)
            tasks.extend(tasks_in_play)
        return tasks

    @property
    def resolver_targets(self):
        return self.roles + self.tasks
        
@dataclass
class Repository(JSONSerializable, Resolvable):
    name: str = ""
    path: str = ""

    my_collection_name: str = ""    # if set, this repository is a collection repository
    
    playbooks: list = field(default_factory=list)
    roles: list = field(default_factory=list)

    installed_collections_path: str = ""
    installed_collections: list = field(default_factory=list)

    installed_roles_path: str = ""
    installed_roles: list = field(default_factory=list)
    
    modules: list = field(default_factory=list)
    taskfiles: list = field(default_factory=list)
    version: str = ""

    module_dict: dict = field(default_factory=dict) # make it easier to search a module
    task_dict: dict = field(default_factory=dict) # make it easier to search a task
    taskfile_dict: dict = field(default_factory=dict) # make it easier to search a taskfile
    role_dict: dict = field(default_factory=dict) # make it easier to search a role

    annotations: dict = field(default_factory=dict)

    def load(self, path="", installed_collections_path="", installed_roles_path="", my_collection_name=""):
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

        logging.info("start loading the repo {}".format(repo_path))
        logging.info("start loading playbooks")
        self.load_playbooks(repo_path)
        logging.info("done ... {} playbooks loaded".format(len(self.playbooks)))
        logging.info("start loading roles")
        self.load_roles(repo_path)
        logging.info("done ... {} roles loaded".format(len(self.roles)))
        logging.info("start loading modules (that are defined in this repository)")
        self.load_modules(repo_path)
        logging.info("done ... {} modules loaded".format(len(self.modules)))
        logging.info("start loading taskfiles (that are defined for playbooks in this repository)")
        self.load_taskfiles(repo_path)
        logging.info("done ... {} task files loaded".format(len(self.taskfiles)))
        logging.info("start loading installed collections")
        self.load_installed_collections(installed_collections_path)
        logging.info("done ... {} collections loaded".format(len(self.installed_collections)))
        logging.info("start loading installed roles")
        self.load_installed_roles(installed_roles_path)
        logging.info("done ... {} roles loaded".format(len(self.installed_roles)))
        self.path = repo_path
        self.installed_collections_path = installed_collections_path
        self.installed_roles_path = installed_roles_path
        logging.info("done")

    def load_playbooks(self, path):
        if path == "":
            return
        patterns = [
            path + "/*.yml",
            path + "/*.yaml",
            path + "/playbooks/**/*.yml",
            path + "/playbooks/**/*.yaml",
        ]
        candidates = []
        for p in patterns:
             found_ones = glob.glob(p, recursive=True)
             candidates.extend(found_ones)
        tasks = []
        playbooks = []
        for fpath in candidates:
            if could_be_playbook(fpath):
                if "/roles/" in fpath:
                    continue
                p = Playbook()
                try:
                    p.load(fpath)
                except PlaybookFormatError as e:
                    logging.debug("this file is not in the playbook format, maybe not a playbook file: {}".format(e.args[0]))
                except:
                    logging.exception("error while loading the playbook at {}".format(fpath))
                playbooks.append(p)
                tasks.extend(p.tasks)
        self.playbooks = playbooks
        self.update_task_dict(tasks)

    def load_roles(self, path):
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
        modules = []
        tasks = []
        taskfiles = []
        roles = []
        for dir_name in dirs:
            role_dir = os.path.join(roles_dir_path, dir_name)
            r = Role()
            try:
                r.load(role_dir)
            except:
                logging.exception("error while loading the role at {}".format(role_dir))
            roles.append(r)
            taskfiles.extend(r.taskfiles)
            for tf in r.taskfiles:
                tasks.extend(tf.tasks)
            modules.extend(r.modules)
        self.roles = roles
        self.update_role_dict(roles)
        self.update_task_dict(tasks)
        self.update_taskfile_dict(taskfiles)
        self.update_module_dict(modules)

    def load_installed_collections(self, installed_collections_path):
        search_path = installed_collections_path
        if installed_collections_path == "" or not os.path.exists(search_path):
            return
        if os.path.exists(os.path.join(search_path, "ansible_collections")):
            search_path = os.path.join(search_path, "ansible_collections")
        dirs = os.listdir(search_path)
        modules = []
        tasks = []
        taskfiles = []
        roles = []
        collections = []
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
                    c.load(collection_dir=collection_path)
                except:
                    logging.exception("error while loading the collection at {}".format(collection_path))
                collections.append(c)
                modules.extend(c.modules)
                roles.extend(c.roles)
                for r in c.roles:
                    taskfiles.extend(r.taskfiles)
                    for tf in r.taskfiles:
                        tasks.extend(tf.tasks)
        self.installed_collections = collections
        builtin = self.parepare_ansible_builtin_collection()
        modules.extend(builtin.modules)
        self.update_module_dict(modules)
        self.update_task_dict(tasks)
        self.update_taskfile_dict(taskfiles)
        self.update_role_dict(roles)

    def load_installed_roles(self, installed_roles_path):
        search_path = installed_roles_path
        if installed_roles_path == "" or not os.path.exists(search_path):
            return
        dirs = os.listdir(search_path)
        modules = []
        tasks = []
        taskfiles = []
        roles = []
        for d in dirs:
            role_path = os.path.join(installed_roles_path, d)
            role_meta_files = glob.glob(role_path + "/**/meta/main.yml", recursive=True)

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
                    r.load(role_dir_path, module_dir_paths=module_dir_paths)
                except:
                    logging.exception("error while loading the role at {}".format(role_dir_path))
                roles.append(r)
                taskfiles.extend(r.taskfiles)
                for tf in r.taskfiles:
                    tasks.extend(tf.tasks)
                modules.extend(r.modules)
        self.installed_roles = roles
        self.update_role_dict(roles)
        self.update_task_dict(tasks)
        self.update_taskfile_dict(taskfiles)
        self.update_module_dict(modules)

    # modules defined in a SCM repo should be in `library` directory in the best practice case
    # https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html
    # however, it is often defined in `plugins/modules` directory in a collection repository,
    # so we search both the directories
    def load_modules(self, path):
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
                    m.load(module_file_path, collection_name=self.my_collection_name)
                except:
                    logging.exception("error while loading the module at {}".format(module_file_path))
                modules.append(m)
            self.modules = modules
            self.update_module_dict(modules)

    # playbooks possibly include/import task files around the playbook file
    # we search this type of isolated taskfile (means not in a role) in `playbooks` and `tasks` dir
    def load_taskfiles(self, path):
        if not os.path.exists(path):
            return
        
        taskfile_paths = search_taskfiles_for_playbooks(path)
        if len(taskfile_paths) > 0:
            taskfiles = []
            for taskfile_path in taskfile_paths:
                tf = TaskFile()
                try:
                    tf.load(taskfile_path)
                except:
                    logging.exception("error while loading the task file at {}".format(taskfile_path))
                taskfiles.append(tf)
            self.taskfiles = taskfiles
            self.update_taskfile_dict(taskfiles)

    def find_my_collection_name(self, path):
        found_galaxy_ymls = glob.glob(path + "/**/galaxy.yml", recursive=True)
        my_collection_name = ""
        if len(found_galaxy_ymls) > 0:
            galaxy_yml = found_galaxy_ymls[0]
            my_collection_info = None
            with open(galaxy_yml, "r") as file:
                my_collection_info = yaml.safe_load(file)
            if my_collection_info is None:
                raise ValueError("failed to read galaxy.yml")
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

    def parepare_ansible_builtin_collection(self):
        builtin_modules = BuiltinModuleSet().builtin_modules
        modules = []
        for bm in builtin_modules:
            fqcn = "ansible.builtin.{}".format(bm)
            m = Module(name=bm, fqcn=fqcn, collection="ansible.builtin", defined_in="", builtin=True)
            modules.append(m)
        c = Collection(name="ansible.builtin", path="", modules=modules)
        return c

    def update_module_dict(self, modules):
        if modules is None:
            return
        module_dict = self.module_dict
        for m in modules:
            if m.fqcn == "":
                continue
            if m.fqcn in module_dict:
                continue
            module_dict[m.fqcn] = m
        self.module_dict = module_dict
        return

    def update_task_dict(self, tasks):
        if tasks is None:
            return
        task_dict = self.task_dict
        for t in tasks:
            if t.id == "":
                continue
            if t.id in task_dict:
                continue
            task_dict[t.id] = t
        self.task_dict = task_dict
        return

    def update_taskfile_dict(self, taskfiles):
        if taskfiles is None:
            return
        taskfile_dict = self.taskfile_dict
        for tf in taskfiles:
            if tf.defined_in == "":
                continue
            if tf.defined_in in taskfile_dict:
                continue
            taskfile_dict[tf.defined_in] = tf
        self.taskfile_dict = taskfile_dict
        return

    def update_role_dict(self, roles):
        if roles is None:
            return
        role_dict = self.role_dict
        for r in roles:
            if r.fqcn == "":
                continue
            if r.fqcn in role_dict:
                continue
            role_dict[r.fqcn] = r
        self.role_dict = role_dict
        return
            
    def get_module_by_fqcn(self, fqcn):
        return self.module_dict.get(fqcn, None)

    def get_module_by_short_name(self, short_name):
        module_dict = self.module_dict
        m = None
        if short_name in module_dict:
            # if a module is defined as a local plugin in the repo, 
            # it does not have a fqcn, so use its short name instead
            m = module_dict[short_name]
        else:
            for key in module_dict:
                if key.endswith(".{}".format(short_name)):
                    m = module_dict[key]
                    break
        return m

    def get_task_by_id(self, id):
        return self.task_dict.get(id, None)

    def get_taskfile_by_path(self, taskfile_path):
        return self.taskfile_dict.get(taskfile_path, None)

    def get_role_by_fqcn(self, fqcn):
        return self.role_dict.get(fqcn, None)

    def get_role_by_short_name(self, short_name):
        role_dict = self.role_dict
        r = None
        if short_name in role_dict:
            # if a role is defined as a local role in the repo, 
            # it does not have a fqcn, so use its short name instead
            r = role_dict[short_name]
        else:
            for key in role_dict:
                if key.endswith(".{}".format(short_name)):
                    r = role_dict[key]
                    break
        return r

    def get_all_modules_in_task(self, obj):
        if not isinstance(obj, Task):
            raise ValueError("this function accepts only Task input, but got {}".format(type(obj).__name__))
        task = obj
        tasks = self.get_all_tasks_called_from_one_task(task)
        modules = []
        for t in tasks:
            if t.executable_type == "Module":
                m = self.get_module_by_fqcn(t.resolved_name)
                modules.append(m)
        return modules

    def get_all_tasks_called_from_one_task(self, obj):
        if not isinstance(obj, Task):
            raise ValueError("this function accepts only Task input, but got {}".format(type(obj).__name__))
        task = obj
        if task.resolved_name == "":
            if task.executable == "":
                return []
            elif task.executable_type == "TaskFile" and "{{" in task.executable:
                # if the target task file for include/import tasks is a variable, we cannot find the target object
                # so just return empty
                return []
            else:
                raise ValueError("FQCN for this task (executable: {} in {}) is empty; need to resolve FQCNs for all tasks first".format(task.executable, task.id))
        tasks = [task]
        if task.executable_type == "Role":
            role_fqcn = task.resolved_name
            r = self.get_role_by_fqcn(role_fqcn)
            for tf in r.taskfiles:
                # call this function recusively for the case like below
                # Task A --import_role--> Role B --run--> Task B2 --include_role--> Role C --run--> Task C1 ...
                for t in tf.tasks:
                    tasks_in_t = self.get_all_tasks_called_from_one_task(t)
                    tasks.extend(tasks_in_t)
        elif task.executable_type == "TaskFile":
            taskfile_path = task.resolved_name
            if taskfile_path != "":
                tf = self.get_taskfile_by_path(taskfile_path)
                if tf is not None:
                    # call this function recusively for the case like below
                    # Task A --import_tasks--> TaskFile B --run--> Task B2 --include_tasks--> TaskFile C --run--> Task C1 ...
                    for t in tf.tasks:
                        tasks_in_t = self.get_all_tasks_called_from_one_task(t)
                        tasks.extend(tasks_in_t)
        return tasks

    @property
    def resolver_targets(self):
        return self.playbooks + self.roles + self.modules + self.installed_roles + self.installed_collections


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
        found = []
        found += glob.glob(search_target + "/**/*.yml")
        found += glob.glob(search_target + "/**/*.yaml")
        for f in found:
            # taskfiles in role will be loaded when the role is loaded, so skip
            if "/roles/" in f:
                continue
            # if it is a playbook, skip it
            if could_be_playbook(f):
                continue
            d = None
            with open(f, "r") as file:
                d = yaml.safe_load(file)
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