from dataclasses import dataclass, field
from unicodedata import category
import io
import re
import os
import codecs
from urllib.robotparser import RobotFileParser
import yaml
import glob
import logging


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

@dataclass
class Module:
    name: str = ""
    fqcn: str = ""
    collection: str = ""
    defined_in: str = ""
    builtin: bool = False
    used_in: list = field(default_factory=list) # resolved later

    def load(self, module_file_path):
        if module_file_path == "":
            raise ValueError("require module file path to load a Module")
        if not module_file_path.endswith(".py"):
            raise ValueError("module file path must end with \".py\"")
        file_name = os.path.basename(module_file_path)
        module_name = file_name.replace(".py", "")
        self.name = module_name
        module_base_dir = os.path.dirname(module_file_path)
        while True:
            if not module_base_dir.endswith("/plugins/modules"):
                new_dir = os.path.dirname(module_base_dir)
                if new_dir == module_base_dir:
                    raise ValueError("failed to find \"plugins/modules\" directory")
                module_base_dir = new_dir
            else:
                break
        
        collection_dir = module_base_dir.replace("/plugins/modules", "")
        parts = collection_dir.split("/")
        if len(parts) < 2:
            raise ValueError("collection directory path of this module is wrong")
        collection_name = "{}.{}".format(parts[-2], parts[-1])
        self.collection = collection_name
        self.fqcn = "{}.{}".format(collection_name, module_name)
        self.defined_in = module_file_path
@dataclass
class Collection:
    name: str = ""
    path: str = ""
    modules: list = field(default_factory=list)
    
    playbooks: list = field(default_factory=list)   # TODO: check if playbooks can be defined in collection
    roles: list = field(default_factory=list)       # TODO: check if roles can be defined in collection

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
            m.load(f)
            modules.append(m)
        self.name = collection_name
        self.path = collection_dir
        self.modules = modules

@dataclass
class Task:
    name: str = ""
    module: str = ""    
    index: int = -1
    defined_in: str = ""
    options: dict = field(default_factory=dict)
    module_options: dict = field(default_factory=dict)

    is_in_playbook: bool = False
    is_pre_task: bool = False
    play_index: int = -1
    
    fqcn: str = ""  # resolved later
    used_in: list = field(default_factory=list) # resolved later

    def load(self, path, index, is_in_playbook=False, is_pre_task=False, play_index=-1):
        if not os.path.exists(path):
            raise ValueError("file not found")
        if not path.endswith(".yml") and not path.endswith(".yaml"):
            raise ValueError("task yaml file must be \".yml\" or \".yaml\"")
        data_block = None
        if is_in_playbook:
            data = load_tasks_in_playbook(path)
            if not isinstance(data, list):
                raise ValueError("the yaml file must have list, but got {}".format(type(data).__name__))
            if play_index < 0 or play_index >= len(data):
                raise ValueError("index \"{}\" is wrong; the yaml data has {} plays inside".format(play_index, len(data)))
            key = "pre_tasks" if is_pre_task else "tasks"
            tasks_in_play = data[play_index].get(key, [])
            if index < 0 or index >= len(tasks_in_play):
                raise ValueError("index \"{}\" is wrong; this play has {} tasks inside".format(index, len(tasks_in_play)))
            data_block = tasks_in_play[index]
        else:
            data = load_tasks_yaml(path)
            if not isinstance(data, list):
                raise ValueError("the yaml file must have list, but got {}".format(type(data).__name__))
            if index < 0 or index >= len(data):
                raise ValueError("index \"{}\" is wrong; the yaml data has {} tasks inside".format(index, len(data)))
            data_block = data[index]
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
        self.is_in_playbook = is_in_playbook
        self.is_pre_task = is_pre_task
        self.play_index = play_index

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

def load_tasks_yaml(fpath=""):
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
class Role:
    name: str = ""
    defined_in: str = ""
    task_yamls: list = field(default_factory=list)     # 1 role can have multiple task yamls
    tasks: list = field(default_factory=list)

    source: str = "" # collection/scm repo/galaxy
    modules: list = field(default_factory=list) # no sample
    
    fqcn: str = "" # resolve later

    def load(self, path):
        if not os.path.exists(path):
            raise ValueError("directory not found")
        
        tasks_dir_path = ""
        if path != "":
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

        task_yaml_files = []
        task_yaml_files += glob.glob(tasks_dir_path + "/**/*.yml", recursive=True)
        task_yaml_files += glob.glob(tasks_dir_path + "/**/*.yaml", recursive=True)
        
        tasks = []
        for task_yaml_path in task_yaml_files:
            data = load_tasks_yaml(fpath=task_yaml_path)
            if data is None:
                continue
            for i in range(len(data)):
                t = Task()
                t.load(task_yaml_path, i)
                tasks.append(t)
        self.tasks = tasks
        self.task_yamls = task_yaml_files


@dataclass
class RoleInPlay:
    name: str = ""
    options: dict = field(default_factory=dict)
    defined_in: str = ""
    role_index: int = -1
    play_index: int = -1
    
    role_path: str = "" # resolved later

@dataclass
class Playbook:
    name: str = ""
    defined_in: str = ""
    
    tasks: list = field(default_factory=list)
    roles: list = field(default_factory=list)   # not actual Role, but RoleInPlay defined in this playbook

    source: str = "" # collection/scm repo
    used_in: list = field(default_factory=list) # resolved later    

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
        tasks = []
        for i, play_dict in enumerate(data):
            if "roles" in play_dict:
                for j, r_dict in enumerate(play_dict.get("roles", [])):
                    r_name = r_dict.get("role", "")
                    role_options = {}
                    for k, v in r_dict.items():
                        role_options[k] = v
                    r = RoleInPlay(name=r_name, options=role_options, defined_in=path, role_index=j, play_index=i)
                    roles.append(r)
            if "tasks" in play_dict:
                for j, _ in enumerate(play_dict.get("tasks", [])):
                    t = Task()
                    t.load(path=path, index=j, is_in_playbook=True, is_pre_task=False, play_index=i)
                    tasks.append(t)
            if "pre_tasks" in play_dict:
                for j, _ in enumerate(play_dict.get("pre_tasks", [])):
                    t = Task()
                    t.load(path=path, index=j, is_in_playbook=True, is_pre_task=True, play_index=i)
                    tasks.append(t)

        self.tasks = tasks
        self.roles = roles
        

@dataclass
class Repository:
    name: str = ""
    path: str = ""
    
    playbooks: list  = field(default_factory=list)
    roles: list  = field(default_factory=list)

    collections_path: str = ""
    collections: list  = field(default_factory=list)

    # modules defined in a SCM repo should be in `library` directory in the best practice case
    # https://docs.ansible.com/ansible/2.8/user_guide/playbooks_best_practices.html
    # but no sample in debops example
    modules: list  = field(default_factory=list)
    version: str = ""

    def load(self, repo_path, collections_path):
        print("start repo loading")
        print("start playbook loading")
        self.load_playbooks(repo_path)
        print("done ... {} playbooks loaded".format(len(self.playbooks)))
        print("start role loading")
        self.load_roles(repo_path)
        print("done ... {} roles loaded".format(len(self.roles)))
        print("start collection loading")
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
        module_dict = {}
        for c in self.collections:
            for m in c.modules:
                module_dict[m.fqcn] = m
        return module_dict

    def get_module(self, fqcn):
        module_dict = self.get_module_dict()
        if fqcn not in module_dict:
            return None
        return module_dict[fqcn]

    def get_role_dict(self):
        role_dict = {}
        for r in self.roles:
            role_dict[r.name] = r
        return role_dict

    def get_role(self, role_name):
        role_dict = self.get_role_dict()
        if role_name not in role_dict:
            return None
        return role_dict[role_name]


