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

#
#  data structure and the relationship between objects
# 
#     Repository
#     |-- Collection
#     |   `-- Module
#     |       `-- "used_in": a list of Tasks that use this module
#     |
#     |-- Playbook
#     |   |-- RoleInPlay
#     |   |   `-- "role_path": a resolved path to the corresponding Role
#     |   |
#     |   `-- Task
#     |       |-- "fqcn": a resolved FQCN of the module for this Task
#     |       `-- "used_in": a list of Playbooks/Roles that use this task
#     `-- Role
#         |-- Module
#         |   `-- same as Collection.Module
#         |
#         |-- Task
#         |   `-- same as Playbook.Task
#         |
#         `-- "used_in": a list of Playbooks that use this Role
#


valid_playbook_re = re.compile(r'^\s*?-?\s*?(?:hosts|include|import_playbook):\s*?.*?$')
module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')
collection_info_dir_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+-[0-9]+\.[0-9]+\.[0-9]\.info$')

@dataclass
class AnsibleConfig:
    collections_path: str = ""
    config_path: str = ""

    def set(self, collections_path="", config_path=""):
        self.collections_path = collections_path
        self.config_path = config_path

config = AnsibleConfig()

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
        return jsonpickle.encode(self)

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
        if not module_file_path.endswith(".py"):
            raise ValueError("module file path must end with \".py\"")
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
    modules: list = field(default_factory=list)
    
    playbooks: list = field(default_factory=list)   # TODO: check if playbooks can be defined in collection
    roles: list = field(default_factory=list)       # TODO: check if roles can be defined in collection

    annotations: dict = field(default_factory=dict)

    def load(self, collection_dir):
        if not os.path.exists(collection_dir):
            raise ValueError("directory not found")
        if not os.path.exists(os.path.join(collection_dir, "plugins/modules")):
            raise ValueError("plugins/modules not found in the collection directory")
        parts = collection_dir.split("/")
        if len(parts) < 2:
            raise ValueError("collection directory path is wrong")
        collection_name = "{}.{}".format(parts[-2], parts[-1])
        module_files = glob.glob(collection_dir + "/plugins/modules/**/*.py", recursive=True)
        modules = []
        for f in module_files:
            m = Module()
            m.load(f, collection_name=collection_name)
            modules.append(m)
        self.name = collection_name
        self.path = collection_dir
        self.modules = modules

    @property
    def resolver_targets(self):
        return self.modules

@dataclass
class Task(JSONSerializable, Resolvable):
    name: str = ""
    module: str = ""    
    index: int = -1
    defined_in: str = ""
    options: dict = field(default_factory=dict)
    module_options: dict = field(default_factory=dict)
    
    fqcn: str = ""  # resolved later
    used_in: list = field(default_factory=list) # resolved later

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
        task_options = {}
        module_options = {}
        for k, v in data_block.items():
            if k == "name":
                task_name = v
            if k == module_name:
                module_options = v
            else:
                task_options.update({k: v})
        self.name = task_name
        self.options = task_options
        self.module = module_name
        self.module_options = module_options
        self.defined_in = path 
        self.index = index

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

def load_tasks_in_playbook(fpath=""):
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
    for i, play_dict in enumerate(d):
        tasks_in_play = {}
        tmp_tasks = play_dict.get("tasks", [])
        tmp_pre_tasks = play_dict.get("pre_tasks", [])
        for task_dict in tmp_tasks:
            task_dict_loop = [task_dict]
            if "block" in task_dict:    # tasks defined in a "block" are flattened
                task_dict_loop = task_dict.get("block", [])
            if "tasks" not in tasks_in_play:
                tasks_in_play["tasks"] = []
            tasks_in_play["tasks"].extend(task_dict_loop)
        for task_dict in tmp_pre_tasks:
            task_dict_loop = [task_dict]
            if "block" in task_dict:    # tasks defined in a "block" are flattened
                task_dict_loop = task_dict.get("block", [])
            if "pre_tasks" not in tasks_in_play:
                tasks_in_play["pre_tasks"] = []
            tasks_in_play["pre_tasks"].extend(task_dict_loop)
        tasks.append(tasks_in_play)
    return tasks

@dataclass
class Role(JSONSerializable, Resolvable):
    name: str = ""
    defined_in: str = ""
    task_yamls: list = field(default_factory=list)     # 1 role can have multiple task yamls
    tasks: list = field(default_factory=list)
    modules: list = field(default_factory=list)     # roles/xxxx/library/zzzz.py can be called as module zzzz

    source: str = "" # collection/scm repo/galaxy
    
    
    fqcn: str = "" # resolve later

    annotations: dict = field(default_factory=dict)

    def load(self, path):
        if not os.path.exists(path):
            raise ValueError("directory not found")
        
        modules_dir_path = ""
        tasks_dir_path = ""
        if path != "":
            modules_dir_path = os.path.join(path, "library")
            tasks_dir_path = os.path.join(path, "tasks")
        
        parts = tasks_dir_path.split("/")
        if len(parts) < 2:
            raise ValueError("role path is wrong")
        role_name = parts[-2]
        self.name = role_name
        self.defined_in = path
        if not os.path.exists(tasks_dir_path):
            # a role possibly has no tasks
            return

        modules = []
        if os.path.exists(modules_dir_path):
            module_files = glob.glob(modules_dir_path + "/**/*.py", recursive=True)
            for module_file_path in module_files:
                if module_file_path.endswith("/__init__.py"):
                    continue
                m = Module()
                m.load(module_file_path, role_name=role_name)
                modules.append(m)
            self.modules = modules

        task_yaml_files = []
        task_yaml_files += glob.glob(tasks_dir_path + "/**/*.yml", recursive=True)
        task_yaml_files += glob.glob(tasks_dir_path + "/**/*.yaml", recursive=True)
        
        tasks = []
        for task_yaml_path in task_yaml_files:
            loaded_tasks = self.get_task_blocks(task_yaml_path)
            if loaded_tasks is None:
                continue
            for index, t_block in enumerate(loaded_tasks):
                t = Task()
                t.load(task_yaml_path, index, t_block)
                tasks.append(t)
        self.tasks = tasks
        self.task_yamls = task_yaml_files

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
            task_dict_loop = [task_dict]
            if "block" in task_dict:    # tasks defined in a "block" are flattened
                task_dict_loop = task_dict.get("block", [])
            tasks.extend(task_dict_loop)
        return tasks

    @property
    def resolver_targets(self):
        return self.tasks + self.modules

@dataclass
class RoleInPlay(JSONSerializable, Resolvable):
    name: str = ""
    options: dict = field(default_factory=dict)
    defined_in: str = ""
    role_index: int = -1
    play_index: int = -1
    
    role_path: str = "" # resolved later

    annotations: dict = field(default_factory=dict)

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

        roles = []
        import_playbooks = []
        for i, play_dict in enumerate(data):
            if "roles" in play_dict:
                for j, r_dict in enumerate(play_dict.get("roles", [])):
                    r_name = r_dict.get("role", "")
                    role_options = {}
                    for k, v in r_dict.items():
                        role_options[k] = v
                    r = RoleInPlay(name=r_name, options=role_options, defined_in=path, role_index=j, play_index=i)
                    roles.append(r)
            if "import_playbook" in play_dict:
                playbook_dir = os.path.dirname(self.defined_in)
                playbook_path = os.path.join(playbook_dir, play_dict["import_playbook"])
                import_playbooks.append(playbook_path)
        tasks = []
        loaded_tasks = self.get_task_blocks(self.defined_in)
        for index, t_block in enumerate(loaded_tasks):
            t = Task()
            t.load(path=self.defined_in, index=index, task_block_dict=t_block)
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

    galaxy_yml: str = ""   # path to the galaxy.yml if it's there
    my_collection_name: str = ""    # if galaxy.yml is there, this repository is for a collection
    
    playbooks: list  = field(default_factory=list)
    roles: list  = field(default_factory=list)

    collections_path: str = ""
    collections: list  = field(default_factory=list)

    modules: list  = field(default_factory=list)
    version: str = ""

    module_dict: dict = field(default_factory=dict) # make it easier to search a module
    role_dict: dict = field(default_factory=dict) # make it easier to search a role

    annotations: dict = field(default_factory=dict)

    def load(self, repo_path, collections_path):
        self.search_galaxy_yml(repo_path)

        print("start loading the repo")
        print("start loading playbooks")
        self.load_playbooks(repo_path)
        print("done ... {} playbooks loaded".format(len(self.playbooks)))
        print("start loading roles")
        self.load_roles(repo_path)
        print("done ... {} roles loaded".format(len(self.roles)))
        print("start loading modules (that are defined in this repository)")
        self.load_modules(repo_path)
        print("done ... {} modules loaded".format(len(self.modules)))
        print("start loading collections")
        self.load_collections(collections_path)
        print("done ... {} collections loaded".format(len(self.collections)))
        self.path = repo_path
        self.collections_path = collections_path
        print("done")

    def load_playbooks(self, path):
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
        playbooks = []
        for fpath in candidates:
            if self.could_be_playbook(fpath):
                p = Playbook()
                p.load(fpath)
                playbooks.append(p)
        self.playbooks = playbooks

    def load_roles(self, path):
        roles_dir_path = os.path.join(path, "roles")
        if not os.path.exists(roles_dir_path):
            return
        dirs = os.listdir(roles_dir_path)
        roles = []
        for dir_name in dirs:
            role_dir = os.path.join(roles_dir_path, dir_name)
            r = Role()
            r.load(role_dir)
            roles.append(r)
        self.roles = roles

    def load_collections(self, collections_root_path):
        search_path = collections_root_path
        if not os.path.exists(search_path):
            return
        if os.path.exists(os.path.join(search_path, "ansible_collections")):
            search_path = os.path.join(search_path, "ansible_collections")
        dirs = os.listdir(search_path)
        collections = []
        for d in dirs:
            collection_path = ""
            if collection_info_dir_re.match(d):
                collection_name = d.split("-")[0]
                collection_name_parts = collection_name.split(".")
                collection_path = os.path.join(search_path, collection_name_parts[0], collection_name_parts[1])
            if collection_path == "":
                continue
            c = Collection()
            c.load(collection_dir=collection_path)
            collections.append(c)
        self.collections = collections
        self.add_ansible_builtin_collection()

    # modules defined in a SCM repo should be in `library` directory in the best practice case
    # https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html
    # however, it is often defined in `plugins/modules` directory in a collection repository,
    # so we search both the directories
    def load_modules(self, path):
        module_dir_path1 = os.path.join(path, "library")
        module_dir_path2 = os.path.join(path, "plugins/modules")
        if not os.path.exists(module_dir_path1) and not os.path.exists(module_dir_path2):
            return
        
        module_files = []
        module_files += glob.glob(module_dir_path1 + "/**/*.py", recursive=True)
        module_files += glob.glob(module_dir_path2 + "/**/*.py", recursive=True)
        if len(module_files) > 0:
            modules = []
            for module_file_path in module_files:
                if module_file_path.endswith("/__init__.py"):
                    continue
                m = Module()
                m.load(module_file_path, collection_name=self.my_collection_name)
                modules.append(m)
            self.modules = modules

    def search_galaxy_yml(self, path):
        found_galaxy_ymls = glob.glob(path + "/**/galaxy.yml", recursive=True)
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
            self.galaxy_yml = galaxy_yml
            self.my_collection_name = my_collection_name
        return

    def add_ansible_builtin_collection(self):
        builtin_modules = BuiltinModuleSet().builtin_modules
        modules = []
        for bm in builtin_modules:
            fqcn = "ansible.builtin.{}".format(bm)
            m = Module(name=bm, fqcn=fqcn, collection="ansible.builtin", defined_in="", builtin=True)
            modules.append(m)
        c = Collection(name="ansible.builtin", path="", modules=modules)
        self.collections.append(c)
    
    # this method is based on awx code https://github.com/ansible/awx/blob/devel/awx/main/utils/ansible.py#L42-L64
    def could_be_playbook(self, fpath):
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

    def get_module_dict(self):
        if len(self.module_dict) > 0:
            return self.module_dict

        module_dict = {}
        for m in self.modules:
            module_dict[m.fqcn] = m
        for r in self.roles:
            for m in r.modules:
                module_dict[m.fqcn] = m
        for c in self.collections:
            for m in c.modules:
                module_dict[m.fqcn] = m
        self.module_dict = module_dict
        return module_dict

    def get_module_by_fqcn(self, fqcn):
        module_dict = self.get_module_dict()
        return module_dict.get(fqcn, None)

    def get_role_dict(self):
        if len(self.role_dict) > 0:
            return self.role_dict
        
        role_dict = {}
        for r in self.roles:
            role_dict[r.name] = r
        self.role_dict = role_dict
        return role_dict

    def get_role_by_name(self, role_name):
        role_dict = self.get_role_dict()
        return role_dict.get(role_name, None)

    @property
    def resolver_targets(self):
        return self.playbooks + self.roles + self.modules + self.collections

