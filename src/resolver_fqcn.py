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
    def __init__(self, repo_obj=None, path_to_dict1_json=""):
        self.repo = repo_obj
        dict1_pack_path = "dict1_pack.json"
        dict1_pack = None
        if os.path.exists(dict1_pack_path):
            with open(dict1_pack_path, "r") as file:
                dict1_pack = json.load(file)
        if dict1_pack is None:
            raw_module_dict = {}
            raw_taskfile_dict = {}
            raw_role_dict = {}
            if path_to_dict1_json != "":
                d = {}
                with open(path_to_dict1_json, "r") as file:
                    d = json.load(file)
                raw_module_dict = d.get("module", {})
                raw_taskfile_dict = d.get("taskfile", {})
                raw_role_dict = d.get("role", {})

            self.module_dict = raw_module_dict

            self.taskfile_dict = {}
            for k, v in raw_taskfile_dict.items():
                if isinstance(v, dict) and "tasks" in v:
                    v["tasks"] = []
                self.taskfile_dict[k] = v

            self.role_dict = {}
            for k, v in raw_role_dict.items():
                if isinstance(v, dict) and "taskfiles" in v:
                    v["taskfiles"] = []
                self.role_dict[k] = v

            dict1_pack = [
                self.module_dict,
                self.role_dict,
                self.taskfile_dict
            ]
            with open(dict1_pack_path, "w") as file:
                json.dump(dict1_pack, file)
        else:
            self.module_dict = dict1_pack[0]
            self.role_dict = dict1_pack[1]
            self.taskfile_dict = dict1_pack[2]

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
                    # if this is a task in a play and if the play has collections, search role from the specified collections
                    if "collections_in_play" in task.__dict__ and len(task.collections_in_play) > 0:
                        for coll in task.collections_in_play:
                            if not isinstance(coll, str):
                                continue
                            fqcn_cand = "{}.{}".format(coll, task.executable)
                            if self.role_fqcn_exists(fqcn_cand):
                                resolved_name = fqcn_cand
                                break
                    else:
                        my_collection_name = ""
                        if task.collection != "":
                            my_collection_name = task.collection
                        # otherwise, search fqcn from role dict
                        resolved_name = self.search_role_fqcn(task.executable, my_collection_name=my_collection_name)
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
                if "collections_in_play" in roleinplay.__dict__ and len(roleinplay.collections_in_play) > 0:
                    for coll in roleinplay.collections_in_play:
                        if not isinstance(coll, str):
                            continue
                        fqcn_cand = "{}.{}".format(coll, roleinplay.name)
                        if self.role_fqcn_exists(fqcn_cand):
                            resolved_name = fqcn_cand
                            break
                else:
                    my_collection_name = ""
                    if roleinplay.collection != "":
                        my_collection_name = roleinplay.collection
                    else:
                        parts = roleinplay.defined_in.split("/")
                        if len(parts) >= 2:
                            my_collection_name = "{}.{}".format(parts[0], parts[1])
                    resolved_name = self.search_role_fqcn(roleinplay.name, my_collection_name=my_collection_name)
            roleinplay.resolved_name = resolved_name
        if roleinplay.resolved_name == "":
            roleinplay.annotations[self.failed_annotation_key] = True
        else:
            if self.failed_annotation_key in roleinplay.annotations:
                roleinplay.annotations.pop(self.failed_annotation_key, None)
        return

    def search_module_fqcn(self, module_name):
        if self.repo is not None:
            for m in self.repo.modules:
                if m.name == module_name:
                    return m.fqcn
        builtin_modules = BuiltinModuleSet().builtin_modules
        fqcn = ""
        if module_name in builtin_modules:
            fqcn = "ansible.builtin.{}".format(module_name)
        if fqcn == "":
            found_module = self.module_dict.get(module_name, None)
            if found_module is not None:
                fqcn = module_name
        if fqcn == "":
            for k in self.module_dict:
                suffix = ".{}".format(module_name)
                if k.endswith(suffix):
                    fqcn = k
        return fqcn

    def search_taskfile_path(self, task_defined_path, taskfile_ref):
        if self.repo is not None:
            task_dir = os.path.dirname(task_defined_path)
            fpath = os.path.join(task_dir, taskfile_ref)
            fpath = os.path.normpath(fpath)
            for tf in self.repo.taskfiles:
                if tf.defined_in == fpath:
                    return fpath
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

        # try searching the include root in the path
        if "/" in taskfile_ref:
            # tasks/some_dir/sample_taskfile.yml --> /tasks
            include_root_dir_name = "/" + taskfile_ref.split("/")[0]
            # if task_dir is like "role_dir/tasks/some_dir2", then 
            # include_root_path will be like "role_dir"
            if include_root_dir_name in task_dir:
                include_root_path = task_dir.split(include_root_dir_name)[0]
                fpath = os.path.join(include_root_path, taskfile_ref)
                fpath = os.path.normpath(fpath)
                found_tf = self.taskfile_dict.get(fpath, None)
                if found_tf is not None:
                    return fpath
            
            if task_dir.endswith("/tasks"):
                role_dir = os.path.dirname(task_dir)
                fpath = os.path.join(role_dir, taskfile_ref)
                fpath = os.path.normpath(fpath)
                found_tf = self.taskfile_dict.get(fpath, None)
                if found_tf is not None:
                    return fpath
        
        return ""

    def search_role_fqcn(self, role_name, my_collection_name=""):
        if self.repo is not None:
            for r in self.repo.roles:
                if r.name == role_name:
                    return r.fqcn
        if "." not in role_name and my_collection_name != "":
            role_name_cand = "{}.{}".format(my_collection_name, role_name)
            found_role = self.role_dict.get(role_name_cand, None)
            if found_role is not None:
                return role_name_cand
        found_role = self.role_dict.get(role_name, None)
        if found_role is not None:
            return role_name
        else:
            for k in self.role_dict:
                suffix = ".{}".format(role_name)
                if k.endswith(suffix):
                    return k
        return ""
    
    def role_fqcn_exists(self, role_fqcn):
        if self.repo is not None:
            for r in self.repo.roles:
                if r.fqcn == role_fqcn:
                    return True
        return role_fqcn in set(self.role_dict.keys())


def main():
    parser = argparse.ArgumentParser(
        prog='resolver_fqcn.py',
        description='resolve fqcn',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-f', '--filepath', default="", help='path to json file')
    parser.add_argument('-o', '--output', default="", help='path to the output json')
    parser.add_argument('-d', '--dict-path', default="/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/dict1.json", help='path to the dict1 json file')
    parser.add_argument('-a', '--all', action='store_true', help='enable full resolve')

    args = parser.parse_args()

    if args.filepath == "" and not args.all:
        raise ValueError("--filepath (-f) option is required")

    resolver = FQCNResolver(path_to_dict1_json=args.dict_path)

    fpath_list = []
    if args.all:
        basedir = "/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/galaxy"
        outdir = "/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/galaxy_resolved"
        fnames = os.listdir(basedir)
        fpath_list = [(os.path.join(basedir, fname), os.path.join(outdir, fname)) for fname in fnames]
    else:
        fpath_list = [(args.filepath, args.output)]

    num = len(fpath_list)
    for i, (fpath, outpath) in enumerate(fpath_list):
        basename = os.path.basename(fpath)
        print("\r[{}/{}] {}\t\t".format(i+1, num, basename), end="")
        obj_json = ""
        with open(fpath, "r") as file:
            obj_json = file.read()

        obj = None
        if basename.startswith("role-"):
            obj = Role()
        elif basename.startswith("collection-"):
            obj = Collection()
        
        if obj is None:
            raise ValueError("object is None; json file name must start with \"role-\" or \"collection-\"")

        # Role or Collection
        obj.from_json(obj_json)

        obj.resolve(resolver)

        if outpath != "":
            resolved_json = obj.dump()
            with open(outpath, "w") as file:
                file.write(resolved_json)

if __name__ == "__main__":
    main()