import os
import yaml

from struct2 import Task

# class Task:
#     name: str
#     module: str
#     fqcn: str 
#     defined_in: str # task_id
#     parameters: dict
#     options: dict
#     used_in: list

TYPE_COLLECTION = "collection"
TYPE_CUSTOM_MODULE = "custom module"


class TaskLoader(object):
    def __init__(self):
        f = open('task_keywords.txt', 'r')
        self.task_keywords = f.read().splitlines()
        f.close()
        f = open('builtin-modules.txt', 'r')
        self.builtin_modules = f.read().splitlines()
        f.close()

    def get_tasks_from_role(self, dir):
        # roles/role_name/tasks/main.yml
        return Task.load_tasks_from_dir(dir)
        

    def get_tasks_from_collection(self, dir):
        # tmp/ansible_collections/collection/playbooks/tasks
        tasks_dir = os.path.join(dir, "playbooks/tasks")
        return Task.load_tasks_from_dir(tasks_dir)

    def resolve_module(self, module):
        # builtin module
        if module.startswith("ansible.builtin."):
            return TYPE_COLLECTION, "ansible.builtin", module, []
        f = open('builtin-modules.txt', 'r')
        builtin_modules = f.read().splitlines()
        f.close()
        if module in builtin_modules:
            fqcn = "ansible.builtin.{0}".format(module)
            return TYPE_COLLECTION, "ansible.builtin", fqcn, []

        # search module
        # module in collection
        candidate = []
        for m in self._collection_modules:
            if m["name"] == module or m["fqcn"] == module:
                candidate.append(m)
        if len(candidate) == 1:
            return TYPE_COLLECTION, candidate[0]["collection"], candidate[0]["fqcn"], candidate
        elif len(candidate) > 0:
            print(candidate)
            return TYPE_COLLECTION, candidate[0]["collection"], candidate[0]["fqcn"], candidate

        # custom module in library dir
        for cm in self._custom_modules:
            if cm["name"] == module:
                return TYPE_CUSTOM_MODULE, cm["file"], cm["name"], candidate 
        print("No collection/custom module is found", module)
        return "", "", "", candidate
    