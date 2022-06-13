from dataclasses import dataclass
from unicodedata import category
import os
import yaml

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


@dataclass(frozen=True)
class TaskKeywordSet(metaclass=Singleton):
    task_keywords: set

with open('task_keywords.txt', 'r') as f:
    TaskKeywordSet(set(f.read().splitlines()))

@dataclass
class Module:
    name: str
    defined_in: str
    collection_name: str
    fqcn: str # module_id
    collection: str
    category: str
    used_in: list

    def load(module_file_path):
        r = module_file_path.split("/")
        module_file = r[-1]
        module_name = module_file.replace(".py", "")
        module = Module(name=module_name, defined_in=module_file_path)
        module.name = module_name
        module.defined_in = module_file_path
        return module

@dataclass
class Task:
    name: str
    module: str
    index: int
    defined_in: str # task_id
    options: dict
    fqcn: str 
    used_in: list

    def load(task, index, defined_in):
        t = Task()
        t.index = index
        t.defined_in = defined_in
        if 'name' in task:
            t.name = task['name']

        task_keywords = TaskKeywordSet().task_keywords
        options = []
        for k,v in task.items():
            if k == "name":
                t.name = task["name"]
            elif k in task_keywords:
                options.append({k:v})
            elif k.startswith("with_"):
                options.append({k:v})
            else:
                t.module= k
                # fqcn, candidates = self.resolve_module(k)
                # t.fqcn = fqcn
        t.options = options
        return t

    def load_tasks_from_file(task_file):
        tasks = []
        task_list = yaml.safe_load(task_file)
        for i, task in enumerate(task_list):
            t = Task.load(task, i, task_file)
            # if t.module is not None:
            #     fqcn, candidates = self.resolve_module(t.module)
            #     t.fqcn = fqcn
            tasks.append(t)
        return tasks

    def load_tasks_from_dir(dir):
        tasks = []
        files = os.listdir(dir)
        files_file = [f for f in files if os.path.isfile(os.path.join(dir, f))]
        for task_file in files_file:
            tasks_from_file = Task.load_tasks_from_file(task_file)
            tasks.extend(tasks_from_file)
        return tasks

@dataclass
class Playbook:
    name: str
    source: str # collection/scm repo
    tasks: list
    defined_in: str # playbook_id
    used_in: list

    def load_from_file(playbook_path):
        name = ''
        source = playbook_path
        tasks = Task.load_tasks_from_file(playbook_path)
        return Playbook(name, source, tasks)


@dataclass
class Role:
    name: str
    defined_in: str # role_id
    source: str # collection/scm repo/galaxy
    tasks: list
    modules: list

    def load_from_dir(role_dir):
        return Role() # TBD

@dataclass
class Collection:
    modules: list
    playbooks: list
    roles: list
    name: str # collection_id
    version: str



@dataclass
class RoleRepo:
    name: str # role_id
    version: str
    tasks: list
    modules: list

