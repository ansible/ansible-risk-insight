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

@dataclass
class ModuleResolveCache:
    data: dict

    def set(self, short_name, m):
        if self.data is None:
            self.data = {}
        self.data.update({short_name: m})

    def get(self, short_name):
        if self.data is None:
            return None
        return self.data.get(short_name, None)

module_resolve_cache = ModuleResolveCache(data={})

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
class Object:
    name: str
    path: str
    parent: object
    children: list = field(default_factory=list)
    doload: bool = True
    imports: list = field(default_factory=list)

    def __post_init__(self):
        if self.doload:
            self.load()

    # load all children as Object
    # e.g.) A Role loads its "tasks/main.yaml" and the all Tasks are set to self.children
    def load(self):
        raise NotImplementedError

    # print children to stdout; this recursively call dump() of all descendants
    # e.g.) Role.dump() -> Task.dump() for all children -> Module.dump()
    def dump(self, indent_lvl=0):
        indent = " " * indent_lvl
        print("{}{}".format(indent, self.id))
        for c in self.children:
            c.dump(indent_lvl=indent_lvl+4)
        for i in self.imports:
            i.dump(indent_lvl=indent_lvl+4)

    # count all children for each type
    def count(self, tmp_result={}):
        current = tmp_result.get(self.type, 0)
        tmp_result.update({self.type: current + 1})
        for c in self.children:
            tmp_result = c.count(tmp_result)
        return tmp_result

    @property
    def type(self):
        return type(self).__name__

    @property
    def id(self):
        return "{} {} \"{}\"".format(self.type, self.path, self.name)

    @property
    def repo_root_dir(self):
        d = self
        root_dir = None
        top_obj = None
        while True:
            if d.type == "Repository":
                root_dir = d.path
                break
            if d.parent is None:
                top_obj = d
                break
            d = d.parent
        if root_dir is None:
            checkbase = os.path.dirname(top_obj.path)
            for i in range(5):
                checkdir = os.path.join(checkbase, "roles")
                if os.path.exists(checkdir):
                    root_dir = os.path.dirname(checkdir)
                    break
                else:
                    checkbase = os.path.dirname(checkbase)
        if root_dir is None:
            raise ValueError("no Repository is found in the ancestor")
        return root_dir

    @property
    def roles_dir(self):
        return os.path.join(self.repo_root_dir, "roles")

@dataclass
class Module(Object):
    fqcn: str = ""
    parameters: dict = field(default_factory=dict)

    def load(self):
        collections_path = config.collections_path
        if self.fqcn != "" and self.fqcn.startswith("ansible.builtin"):
            return

        m = module_resolve_cache.get(self.name)
        if m is not None:
            self.name = m.name
            self.path = m.path
            self.fqcn = m.fqcn
            return
        
        builtin_modules = BuiltinModuleSet().builtin_modules
        if self.name in builtin_modules:
            self.fqcn = "ansible.builtin.{}".format(self.name)
            module_resolve_cache.set(self.name, self)
            return

        patterns = [
            collections_path + "/**/plugins/modules/**/{}.py".format(self.name),
        ]
        matched_files = []
        for p in patterns:
            candidates = glob.glob(p, recursive=True)
            matched_files.extend(candidates)
        if len(matched_files) == 0:
            raise ValueError("failed to resolve the module \"{}\"".format(self.name))
        
        matched_module_path = matched_files[0]
        self.path = matched_module_path
        if matched_module_path.startswith(collections_path):
            matched_module_path = matched_module_path[len(collections_path):]
        ansible_collections_dirname = "/ansible_collections"
        if matched_module_path.startswith(ansible_collections_dirname):
             matched_module_path = matched_module_path[len(ansible_collections_dirname):]
        parts = [p for p in matched_module_path.split("/") if p != ""]
        if len(parts) < 2:
            raise ValueError("found module path is wrong; {}".format(matched_module_path))
        self.fqcn = "{}.{}.{}".format(parts[0], parts[1], self.name)
        module_resolve_cache.set(self.name, self)
        return

    @property
    def id(self):
        path = "__builtin__" if self.path == "" else self.path
        name = self.name if self.fqcn == "" else self.fqcn
        return "{} {} \"{}\"".format(self.type, path, name)

def load_task_list(fpath=""):
    d = []
    if fpath == "":
        return None
    else:
        if not os.path.exists(fpath):
            return None
        with open(fpath , "r") as file:
            d = yaml.safe_load(file)
    tasks = []
    for task_dict in d:
        task_dict_loop = [task_dict]
        if "block" in task_dict:
            task_dict_loop = task_dict.get("block", [])
        task_yaml_loop = [yaml.safe_dump(li) for li in task_dict_loop]
        tasks.extend(task_yaml_loop)
    return tasks

@dataclass
class Task(Object):
    yaml: str = ""
    parameters: dict = field(default_factory=dict)
    module: object = None

    def load(self):
        d = {}
        if self.yaml != "":
            file = io.StringIO(self.yaml)
            d = yaml.safe_load(file)
        task_name = ""
        module_name = self.find_module_name([k for k in d.keys()])
        task_parameters = {}
        module_parameters = {}
        for k, v in d.items():
            if k == "name":
                task_name = v
            if k == module_name:
                module_parameters = v
            else:
                task_parameters.update({k: v})
        self.name = task_name
        self.parameters = task_parameters
        fqcn = ""
        if module_name_re.match(module_name):
            fqcn = module_name
            module_name = module_name.split(".")[-1]
        try:
            m = Module(name=module_name, fqcn=fqcn, parameters=module_parameters, path="", parent=self)
            self.module = m
            self.resolve_import()
        except Exception as e:
            logging.error(e)
    
    def resolve_import(self):
        role_patterns = ["import_role", "include_role"]
        if self.module.name in role_patterns:
            role_name = self.module.parameters.get("name", None)
            if role_name is None:
                raise ValueError("this {} does not have \"name\" parameter".format(self.module.name))
            role_path = os.path.join(self.roles_dir, role_name)
            r = Role(name=role_name, path=role_path, parent=self)
            self.imports.append(r)
        tasks_patterns = ["import_tasks", "include_tasks", "include"]
        if self.module.name in tasks_patterns:
            tasks_fname = self.module.parameters
            fpath = os.path.join(os.path.dirname(self.path), tasks_fname)
            task_yaml_blocks = load_task_list(fpath)
            if task_yaml_blocks is None:
                return
            tasks = []
            for task_yaml_block in task_yaml_blocks:
                t = Task(name="", path=fpath, yaml=task_yaml_block, parent=self)
                tasks.append(t)
            self.imports.extend(tasks)

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
        return "{} {} \"{}\" {}".format(self.type, self.path, self.name, self.module.fqcn)

@dataclass
class Role(Object):
    def load(self):
        tasks_yaml_path = ""
        if self.path != "":
            tasks_yaml_path = os.path.join(self.path, "tasks/main.yml")
        task_yaml_blocks = load_task_list(tasks_yaml_path)
        if task_yaml_blocks is None:
            return
        tasks = []
        for task_yaml_block in task_yaml_blocks:
            try:
                t = Task(name="", path=tasks_yaml_path, yaml=task_yaml_block, parent=self)
                tasks.append(t)
            except Exception as e:
                logging.error(e)
        self.children = tasks

def load_play_list(fpath=""):
    d = []
    if fpath == "":
        return None
    else:
        if not os.path.exists(fpath):
            return None
        with open(fpath , "r") as file:
            d = yaml.safe_load(file)
    play_dict_blocks = d
    return play_dict_blocks

@dataclass
class Playbook(Object):
    def load(self):
        play_dict_blocks = None
        if self.path != "":
            play_dict_blocks = load_play_list(self.path)
        if play_dict_blocks is None:
            return
        roles_dir = self.roles_dir
        roles = []
        tasks = []
        for play_dict in play_dict_blocks:
            if "roles" in play_dict:
                for r in play_dict.get("roles", []):
                    r_name = r.get("role", "")
                    r_path = os.path.join(roles_dir, r_name)
                    try:
                        r = Role(name=r_name, path=r_path, parent=self)
                        roles.append(r)
                    except Exception as e:
                        logging.error(e)
            if "tasks" in play_dict:
                for t in play_dict.get("tasks", []):
                    task_yaml_block = yaml.safe_dump(t)
                    try:
                        t = Task(name="", path=self.path, yaml=task_yaml_block, parent=self)
                        tasks.append(t)
                    except Exception as e:
                        logging.error(e)
            if "pre_tasks" in play_dict:
                for t in play_dict.get("pre_tasks", []):
                    task_yaml_block = yaml.safe_dump(t)
                    try:
                        t = Task(name="", path=self.path, yaml=task_yaml_block, parent=self)
                        tasks.append(t)
                    except Exception as e:
                        logging.error(e)
        self.children.extend(tasks)
        self.children.extend(roles)
        self.resolve_import(play_dict_blocks)

    def resolve_import(self, play_dict_blocks=[]):
        playbook_patterns = ["import_playbook", "include"]
        playbooks = []
        for play_dict in play_dict_blocks:
            matched = False
            matched_module_name = None
            for module_name in playbook_patterns:
                if module_name in play_dict:
                    matched = True
                    matched_module_name = module_name
                    break
            if matched:
                playbook_name = play_dict.get(matched_module_name, "")
                playbook_path = os.path.join(os.path.dirname(self.path), playbook_name)
                p = Playbook(name=os.path.basename(playbook_path), path=playbook_path, parent=self)
                playbooks.append(p)
        self.imports.extend(playbooks)

@dataclass
class Repository(Object):

    def load(self):
        d = []
        patterns = [
            self.path + "/*.yml",
            self.path + "/*.yaml",
            self.path + "/playbooks/**/*.yml",
            self.path + "/playbooks/**/*.yaml",
        ]
        candidates = []
        for p in patterns:
             found_ones = glob.glob(p, recursive=True)
             candidates.extend(found_ones)
        playbooks = []
        for fpath in candidates:
            if self.could_be_playbook(fpath):
                try:
                    p = Playbook(name=os.path.basename(fpath), path=fpath, parent=self)
                    playbooks.append(p)
                except Exception as e:
                    logging.error(e)
        self.children = playbooks
    
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




