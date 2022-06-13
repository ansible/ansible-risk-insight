import yaml
import os

import struct

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
        tasks = []
        # roles/role_name/tasks/main.yml
        files = os.listdir(dir)
        files_file = [f for f in files if os.path.isfile(os.path.join(dir, f))]
        for task_file in files_file:
            task_list = yaml.safe_load(task_file)
            for task in task_list:
                t = struct.Task()
                t.defined_in = "{0}_{1}".format(files_file, task_list.index(task))
                options = []
                for k,v in task.items():
                    if k == "name":
                        t.name = task["name"]
                    elif k in self.task_keywords:
                        options.append({k:v})
                    elif k.startswith("with_"):
                        options.append({k:v})
                    else:
                        t.module= k
                        # fqcn, candidates = self.resolve_module(k)
                        # t.fqcn = fqcn
                t.options = options
                tasks.append(t)
        return tasks
    
    def get_tasks_from_collection(self, dir):
        # tmp/ansible_collections/collection/playbooks/tasks
        tasks = []
        tasks_dir = os.path.join(dir, "playbooks/tasks")
        files = os.listdir(tasks_dir)
        files_file = [f for f in files if os.path.isfile(os.path.join(tasks_dir, f))]
        for task_file in files_file:
            task_list = yaml.safe_load(task_file)
            for task in task_list:
                t = struct.Task()
                t.defined_in = "{0}_{1}".format(files_file, task_list.index(task))
                options = []
                for k,v in task.items():
                    if k == "name":
                        t.name = task["name"]
                    elif k in self.task_keywords:
                        options.append({k:v})
                    elif k.startswith("with_"):
                        options.append({k:v})
                    else:
                        t.module= k
                        fqcn, candidates = self.resolve_module(k)
                        t.fqcn = fqcn
                t.options = options
                tasks.append(t)
        return tasks

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
    