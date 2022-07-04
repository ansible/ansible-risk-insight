import os
import re
import json
import argparse
from struct4 import BuiltinModuleSet, Role, Collection
from resolver import Resolver
import logging


module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')
role_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+$')
role_in_collection_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

# set fqcn to all Task and RoleInPlay
class FQCNResolver(Resolver):
    def __init__(self, path_to_dict1_json=""):
        self.module_dict = {}
        self.taskfile_dict = {}
        self.role_dict = {}
        if path_to_dict1_json != "":
            d = {}
            with open(path_to_dict1_json, "r") as file:
                d = json.load(file)
            self.module_dict = d.get("module", {})
            self.taskfile_dict = d.get("taskfile", {})
            self.role_dict = d.get("role", {})

        self.module_fqcn_dict = {}
        for k in self.module_dict:
            short_name = k.split(".")[-1]
            self.module_fqcn_dict[short_name] = k

        self.role_fqcn_dict = {}
        for k in self.role_dict:
            short_name = k.split(".")[-1]
            self.role_fqcn_dict[short_name] = k

        self.failed_annotation_key = "fqcn-resolve-failed"

    def task(self, obj):
        super().task(obj)
        task = obj
        if task.module == "":
            return
        if task.resolved_name == "":
            resolved_name = ""
            if task.executable_type == "Module":            
                # if the module name is in fqcn format, just set it
                if module_name_re.match(task.executable):
                    resolved_name = task.module
                else:
                    # otherwise, search fqcn from module dict
                    resolved_name = self.search_module_fqcn(task.module)
                    if resolved_name == "":
                        logging.warning("module \"{}\" not found for task \"{}\"".format(task.module, task.id))
            elif task.executable_type == "TaskFile":
                resolved_name = self.search_taskfile_path(task.defined_in, task.executable)
                if resolved_name == "":
                    # if "{{" is found in the target path for include_tasks/import_tasks, 
                    # task file reference is parameterized, so give up to get fqcn in the case.
                    if "{{" in task.executable:
                        logging.debug("task file \"{}\" is including variable and we cannot resolve this for the task \"{}\"".format(task.executable, task.id))
                        pass
                    else:
                        # otherwise, the path should be resolved but not found. warn it here.
                        logging.warning("task file \"{}\" not found for task \"{}\"".format(task.executable, task.id))
            elif task.executable_type == "Role":
                # if the role name is in fqcn format, just set it
                if role_name_re.match(task.executable):
                    resolved_name = task.executable
                elif role_in_collection_name_re.match(task.executable):
                    resolved_name = task.executable
                else:
                    # otherwise, search fqcn from module dict
                    resolved_name = self.search_role_fqcn(task.executable)
                    if resolved_name == "":
                        logging.warning("role \"{}\" not found for task \"{}\"".format(task.executable, task.id))
            else:
                if task.executable == "":
                    raise ValueError("the executable type is not set")
                else:
                    raise ValueError("the executable type {} is not supported".format(task.executable))
            task.resolved_name = resolved_name
        if task.resolved_name == "":
            task.annotations[self.failed_annotation_key] = True
        else:
            if self.failed_annotation_key in task.annotations:
                task.annotations.pop(self.failed_annotation_key, None)
        return

    def roleinplay(self, obj):
        super().roleinplay(obj)
        roleinplay = obj
        if roleinplay.resolved_name == "":
            resolved_name = ""
            if role_name_re.match(roleinplay.name):
                resolved_name = roleinplay.name
            else:
                resolved_name = self.search_role_fqcn(roleinplay.name)
            roleinplay.resolved_name = resolved_name
        if roleinplay.resolved_name == "":
            roleinplay.annotations[self.failed_annotation_key] = True
        else:
            if self.failed_annotation_key in roleinplay.annotations:
                roleinplay.annotations.pop(self.failed_annotation_key, None)
        return

    def search_module_fqcn(self, module_name):
        builtin_modules = BuiltinModuleSet().builtin_modules
        fqcn = ""
        if module_name in builtin_modules:
            fqcn = "ansible.builtin.{}".format(module_name)
        if fqcn == "":
            found_fqcn = self.module_fqcn_dict.get(module_name, None)
            if found_fqcn is None:
                return ""
            fqcn = found_fqcn
        return fqcn

    def search_taskfile_path(self, task_defined_path, taskfile_ref):
        # include/import tasks can have a path like "roles/xxxx/tasks/yyyy.yml"
        # then try to find roles directory
        if taskfile_ref.startswith("roles/"):
            if "/roles/" in task_defined_path:
                roles_parent_dir = task_defined_path.split("/roles/")[0]
                fpath = os.path.join(roles_parent_dir, taskfile_ref)
                fpath = os.path.normpath(fpath)
                found_tf = self.taskfile_dict.get(fpath, None)
                if found_tf is not None:
                    return fpath

        task_dir = os.path.dirname(task_defined_path)
        fpath = os.path.join(task_dir, taskfile_ref)
        # need to normalize path here because taskfile_ref can be smoething like "../some_taskfile.yml",
        # but "tasks/some_dir/../some_taskfile.yml" cannot be found in the taskfile_dict
        # it will be "tasks/some_taskfile.yml" by this normalize
        fpath = os.path.normpath(fpath)
        found_tf = self.taskfile_dict.get(fpath, None)
        if found_tf is not None:
            return fpath
        return ""

    def search_role_fqcn(self, role_name):
        found_fqcn = self.role_fqcn_dict.get(role_name, None)
        if found_fqcn is None:
            return ""
        return found_fqcn


def main():
    parser = argparse.ArgumentParser(
        prog='resolver_fqcn.py',
        description='resolve fqcn',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-f', '--filepath', default="", help='path to json file')
    parser.add_argument('-o', '--output', default="", help='path to the output json')
    parser.add_argument('-d', '--dict-path', default="", help='path to the dict1 json file')

    args = parser.parse_args()

    if args.filepath == "":
        raise ValueError("--filepath (-f) option is required")

    obj_json = ""
    with open(args.filepath, "r") as file:
        obj_json = file.read()

    obj = None
    basename = os.path.basename(args.filepath)
    if basename.startswith("role-"):
        obj = Role()
    elif basename.startswith("collection-"):
        obj = Collection()
    
    if obj is None:
        raise ValueError("object is None; json file name must start with \"role-\" or \"collection-\"")

    # Role or Collection
    obj.from_json(obj_json)

    resolver = FQCNResolver(args.dict_path)
    obj.resolve(resolver)

    if args.output != "":
        resolved_json = obj.dump()
        with open(args.output, "w") as file:
            file.write(resolved_json)

if __name__ == "__main__":
    