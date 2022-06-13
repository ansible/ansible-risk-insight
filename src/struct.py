from dataclasses import dataclass
from unicodedata import category

@dataclass
class Module:
    name: str
    collection_name: str
    fqcn: str # module_id
    defined_in: str
    collection: str
    category: str
    used_in: list

@dataclass
class Task:
    name: str
    module: str
    fqcn: str 
    defined_in: str # task_id
    parameters: dict
    options: dict
    used_in: list

@dataclass
class Role:
    name: str
    defined_in: str # role_id
    source: str # collection/scm repo/galaxy
    tasks: list
    modules: list

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

@dataclass
class Playbook:
    name: str
    source: str # collection/scm repo
    defined_in: str # playbook_id
    used_in: list