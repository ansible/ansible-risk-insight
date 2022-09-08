import os
import re
import json
import argparse
import joblib
import shutil
from models import ObjectList, Load
from resolver import Resolver
import logging
from finder import get_builtin_module_names


module_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")
role_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
role_in_collection_name_re = re.compile(
    r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$"
)


# set fqcn to all Task and RoleInPlay
class FQCNResolver(Resolver):
    def __init__(self, repo_obj=None, path_to_dict1_json="", dicts={}):
        self.repo = repo_obj
        dict1_pack_path = "dict1_pack.json"
        dict1_pack = None
        if len(dicts) == 3:
            self.module_dict = dicts.get("module", {})
            self.role_dict = dicts.get("role", {})
            self.taskfile_dict = dicts.get("taskfile", {})
        elif os.path.exists(dict1_pack_path):
            with open(dict1_pack_path, "r") as file:
                dict1_pack = json.load(file)
        elif dict1_pack is None:
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
                self.taskfile_dict,
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
                        logging.warning(
                            'module "{}" not found for task "{}"'.format(
                                task.module, task.id
                            )
                        )
            elif task.executable_type == "TaskFile":
                resolved_name = self.search_taskfile_path(
                    task.defined_in, task.executable
                )
                if resolved_name == "":
                    # if the task file reference is parameterized
                    # give up to get the fqcn.
                    if "{{" in task.executable:
                        logging.debug(
                            'task file "{}" is including variable and we'
                            ' cannot resolve this for the task "{}"'.format(
                                task.executable, task.id
                            )
                        )
                        pass
                    else:
                        # otherwise, the path should be resolved but
                        # it was not found. warn it here.
                        logging.warning(
                            'task file "{}" not found for task "{}"'.format(
                                task.executable, task.id
                            )
                        )
            elif task.executable_type == "Role":
                # if the role name is in fqcn format, just set it
                if role_name_re.match(task.executable):
                    resolved_name = task.executable
                elif role_in_collection_name_re.match(task.executable):
                    resolved_name = task.executable
                else:
                    # if this is task in play and if the play has collections,
                    # search role from the specified collections
                    if (
                        "collections_in_play" in task.__dict__
                        and len(task.collections_in_play) > 0
                    ):
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
                        resolved_name = self.search_role_fqcn(
                            task.executable,
                            my_collection_name=my_collection_name,
                        )
                    if resolved_name == "":
                        logging.warning(
                            'role "{}" not found for task "{}"'.format(
                                task.executable, task.id
                            )
                        )
            else:
                if task.executable == "":
                    raise ValueError("the executable type is not set")
                else:
                    raise ValueError(
                        "the executable type {} is not supported".format(
                            task.executable
                        )
                    )
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
                if (
                    "collections_in_play" in roleinplay.__dict__
                    and len(roleinplay.collections_in_play) > 0
                ):
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
                            my_collection_name = "{}.{}".format(
                                parts[0], parts[1]
                            )
                    resolved_name = self.search_role_fqcn(
                        roleinplay.name, my_collection_name=my_collection_name
                    )
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
        builtin_modules = get_builtin_module_names()
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
        # need to normalize path here because taskfile_ref can be
        # something like "../some_taskfile.yml".
        # it should be "tasks/some_taskfile.yml"
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


def get_dependency_names(raw_dependencies):
    if not isinstance(raw_dependencies, dict):
        return [], []
    raw_dep_roles = raw_dependencies.get("roles", [])
    raw_dep_colls = raw_dependencies.get("collections", [])

    dep_roles = []
    if isinstance(raw_dep_roles, list):
        for dep in raw_dep_roles:
            if isinstance(dep, str):
                dep_roles.append(dep)
            elif isinstance(dep, dict):
                r_name = dep.get("role", "")
                if r_name != "":
                    dep_roles.append(dep)
    dep_colls = []
    if isinstance(raw_dep_colls, list):
        for dep in raw_dep_colls:
            if isinstance(dep, str):
                dep_colls.append(dep)
    # Collection.dependency["collections"] is a dict like below
    #   "community.general": "1.0.0",
    #   "ansible.posix": "*",
    elif isinstance(raw_dep_colls, dict):
        for c_name in raw_dep_colls:
            dep_colls.append(c_name)
    return dep_roles, dep_colls


def get_all_dependencies(target_path, known_dependencies={}):
    # TODO: if target is not there, should do install
    # and then load & parse for it dynamically?
    if not os.path.exists(target_path):
        return {"roles": [], "collections": []}
    target = os.path.basename(os.path.normpath(target_path))
    basedir = os.path.dirname(os.path.normpath(target_path))
    target_type = target.split("-")[0]

    target_key = (
        target_type + "s"
    )  # role --> roles, collection --> collections
    if target in known_dependencies.get(target_key, []):
        return {"roles": [], "collections": []}

    raw_dependencies = {}
    if target_type == "collection":
        collections_path = os.path.join(target_path, "collections.json")
        collections = ObjectList().from_json(fpath=collections_path)
        c = collections.items[0]
        raw_dependencies = c.dependency
    elif target_type == "role":
        roles_path = os.path.join(target_path, "roles.json")
        roles = ObjectList().from_json(fpath=roles_path)
        r = roles.items[0]
        raw_dependencies = r.dependency

    dep_roles, dep_colls = get_dependency_names(raw_dependencies)

    dependencies = {}
    dependencies["roles"] = dep_roles
    dependencies["collections"] = dep_colls

    for role_name in dependencies["roles"]:
        sub_target_path = os.path.join(basedir, "role-{}".format(role_name))
        sub_dependencies = get_all_dependencies(
            target_path=sub_target_path, known_dependencies=dependencies
        )
        dependencies["roles"].extend(sub_dependencies["roles"])
        dependencies["collections"].extend(sub_dependencies["collections"])

    for collection_name in dependencies["collections"]:
        sub_target_path = os.path.join(
            basedir, "collection-{}".format(collection_name)
        )
        sub_dependencies = get_all_dependencies(
            target_path=sub_target_path, known_dependencies=dependencies
        )
        dependencies["roles"].extend(sub_dependencies["roles"])
        dependencies["collections"].extend(sub_dependencies["collections"])

    dependencies["roles"] = sorted(dependencies["roles"])
    dependencies["collections"] = sorted(dependencies["collections"])
    return dependencies


def load_definitions(target_path):
    roles_path = os.path.join(target_path, "roles.json")
    roles = ObjectList()
    if os.path.exists(roles_path):
        roles.from_json(fpath=roles_path)
    taskfiles_path = os.path.join(target_path, "taskfiles.json")
    taskfiles = ObjectList()
    if os.path.exists(taskfiles_path):
        taskfiles.from_json(fpath=taskfiles_path)
    modules_path = os.path.join(target_path, "modules.json")
    modules = ObjectList()
    if os.path.exists(modules_path):
        modules.from_json(fpath=modules_path)
    return roles, taskfiles, modules


def make_dicts(target_path, dependencies, galaxy_dir="", save_marged=False):
    basedir = ""
    if galaxy_dir == "":
        basedir = os.path.dirname(os.path.normpath(target_path))
    else:
        basedir = galaxy_dir
    roles, taskfiles, modules = load_definitions(target_path=target_path)

    req_path_list = []
    for role_name in dependencies.get("roles", []):
        req_path_list.append(
            os.path.join(basedir, "role-{}".format(role_name))
        )
    for collection_name in dependencies.get("collections", []):
        req_path_list.append(
            os.path.join(basedir, "collection-{}".format(collection_name))
        )

    for sub_target_path in req_path_list:
        sub_roles, sub_taskfiles, sub_modules = load_definitions(
            target_path=sub_target_path
        )
        roles.merge(sub_roles)
        taskfiles.merge(sub_taskfiles)
        modules.merge(sub_modules)

    if save_marged:
        os.makedirs(os.path.join(target_path, "merged"), exist_ok=True)
        roles.dump(fpath=os.path.join(target_path, "merged", "roles.json"))
        taskfiles.dump(
            fpath=os.path.join(target_path, "merged", "taskfiles.json")
        )
        modules.dump(
            fpath=os.path.join(target_path, "merged", "modules.json")
        )

        # TODO: handle playbook, play and tasks correctly
        shutil.copyfile(
            os.path.join(target_path, "playbooks.json"),
            os.path.join(target_path, "merged/playbooks.json"),
        )
        shutil.copyfile(
            os.path.join(target_path, "plays.json"),
            os.path.join(target_path, "merged/plays.json"),
        )
        shutil.copyfile(
            os.path.join(target_path, "tasks.json"),
            os.path.join(target_path, "merged/tasks.json"),
        )

    role_dict = {}
    for r in roles.items:
        role_dict[r.fqcn] = r
    taskfile_dict = {}
    for tf in taskfiles.items:
        taskfile_dict[tf.defined_in] = tf
    module_dict = {}
    for m in modules.items:
        module_dict[m.fqcn] = m

    dicts = {
        "role": role_dict,
        "taskfile": taskfile_dict,
        "module": module_dict,
    }

    return dicts


def get_dependency_names(raw_dependencies):
    if not isinstance(raw_dependencies, dict):
        return [], []
    raw_dep_roles = raw_dependencies.get("roles", [])
    raw_dep_colls = raw_dependencies.get("collections", [])

    dep_roles = []
    if isinstance(raw_dep_roles, list):
        for dep in raw_dep_roles:
            if isinstance(dep, str):
                dep_roles.append(dep)
            elif isinstance(dep, dict):
                r_name = dep.get("role", "")
                if r_name != "":
                    dep_roles.append(dep)
    dep_colls = []
    if isinstance(raw_dep_colls, list):
        for dep in raw_dep_colls:
            if isinstance(dep, str):
                dep_colls.append(dep)
    # Collection.dependency["collections"] is a dict like below
    #   "community.general": "1.0.0",
    #   "ansible.posix": "*",
    elif isinstance(raw_dep_colls, dict):
        for c_name in raw_dep_colls:
            dep_colls.append(c_name)
    return dep_roles, dep_colls


def get_all_dependencies(target_path, known_dependencies={}):
    # TODO: if target is not there, should do install
    # and then load & parse for it dynamically?
    if not os.path.exists(target_path):
        return {"roles": [], "collections": []}
    target = os.path.basename(os.path.normpath(target_path))
    basedir = os.path.dirname(os.path.normpath(target_path))
    target_type = target.split("-")[0]

    target_key = (
        target_type + "s"
    )  # role --> roles, collection --> collections
    if target in known_dependencies.get(target_key, []):
        return {"roles": [], "collections": []}

    raw_dependencies = {}
    if target_type == "collection":
        collections_path = os.path.join(target_path, "collections.json")
        collections = ObjectList().from_json(fpath=collections_path)
        c = collections.items[0]
        raw_dependencies = c.dependency
    elif target_type == "role":
        roles_path = os.path.join(target_path, "roles.json")
        roles = ObjectList().from_json(fpath=roles_path)
        r = roles.items[0]
        raw_dependencies = r.dependency

    dep_roles, dep_colls = get_dependency_names(raw_dependencies)

    dependencies = {}
    dependencies["roles"] = dep_roles
    dependencies["collections"] = dep_colls

    for role_name in dependencies["roles"]:
        sub_target_path = os.path.join(basedir, "role-{}".format(role_name))
        sub_dependencies = get_all_dependencies(
            target_path=sub_target_path, known_dependencies=dependencies
        )
        dependencies["roles"].extend(sub_dependencies["roles"])
        dependencies["collections"].extend(sub_dependencies["collections"])

    for collection_name in dependencies["collections"]:
        sub_target_path = os.path.join(
            basedir, "collection-{}".format(collection_name)
        )
        sub_dependencies = get_all_dependencies(
            target_path=sub_target_path, known_dependencies=dependencies
        )
        dependencies["roles"].extend(sub_dependencies["roles"])
        dependencies["collections"].extend(sub_dependencies["collections"])

    dependencies["roles"] = sorted(dependencies["roles"])
    dependencies["collections"] = sorted(dependencies["collections"])
    return dependencies


def load_definitions(target_path):
    roles_path = os.path.join(target_path, "roles.json")
    roles = ObjectList()
    if os.path.exists(roles_path):
        roles.from_json(fpath=roles_path)
    taskfiles_path = os.path.join(target_path, "taskfiles.json")
    taskfiles = ObjectList()
    if os.path.exists(taskfiles_path):
        taskfiles.from_json(fpath=taskfiles_path)
    modules_path = os.path.join(target_path, "modules.json")
    modules = ObjectList()
    if os.path.exists(modules_path):
        modules.from_json(fpath=modules_path)
    return roles, taskfiles, modules


def make_dicts(target_path, dependencies, galaxy_dir="", save_marged=False):
    basedir = ""
    if galaxy_dir == "":
        basedir = os.path.dirname(os.path.normpath(target_path))
    else:
        basedir = galaxy_dir
    roles, taskfiles, modules = load_definitions(target_path=target_path)

    req_path_list = []
    for role_name in dependencies.get("roles", []):
        req_path_list.append(
            os.path.join(basedir, "role-{}".format(role_name))
        )
    for collection_name in dependencies.get("collections", []):
        req_path_list.append(
            os.path.join(basedir, "collection-{}".format(collection_name))
        )

    for sub_target_path in req_path_list:
        sub_roles, sub_taskfiles, sub_modules = load_definitions(
            target_path=sub_target_path
        )
        roles.merge(sub_roles)
        taskfiles.merge(sub_taskfiles)
        modules.merge(sub_modules)

    if save_marged:
        os.makedirs(os.path.join(target_path, "merged"), exist_ok=True)
        roles.dump(fpath=os.path.join(target_path, "merged", "roles.json"))
        taskfiles.dump(
            fpath=os.path.join(target_path, "merged", "taskfiles.json")
        )
        modules.dump(
            fpath=os.path.join(target_path, "merged", "modules.json")
        )

        # TODO: handle playbook, play and tasks correctly
        shutil.copyfile(
            os.path.join(target_path, "playbooks.json"),
            os.path.join(target_path, "merged/playbooks.json"),
        )
        shutil.copyfile(
            os.path.join(target_path, "plays.json"),
            os.path.join(target_path, "merged/plays.json"),
        )
        shutil.copyfile(
            os.path.join(target_path, "tasks.json"),
            os.path.join(target_path, "merged/tasks.json"),
        )

    role_dict = {}
    for r in roles.items:
        role_dict[r.fqcn] = r
    taskfile_dict = {}
    for tf in taskfiles.items:
        taskfile_dict[tf.defined_in] = tf
    module_dict = {}
    for m in modules.items:
        module_dict[m.fqcn] = m

    dicts = {
        "role": role_dict,
        "taskfile": taskfile_dict,
        "module": module_dict,
    }

    return dicts


def main():
    parser = argparse.ArgumentParser(
        prog="resolver_fqcn.py",
        description="resolve fqcn",
        epilog="end",
        add_help=True,
    )

    parser.add_argument(
        "-t",
        "--target-path",
        default="",
        help="path to dir which contains load.json",
    )
    parser.add_argument(
        "-a", "--all", action="store_true", help="enable full resolve"
    )

    args = parser.parse_args()

    if not os.path.exists(args.target_path):
        raise ValueError("target directory does not exist")

    profiles = []
    if args.all:
        dirnames = os.listdir(args.target_path)
        for dname in dirnames:
            target_path = os.path.join(args.target_path, dname)
            p = target_path
            profiles.append(p)
    else:
        profiles = [(args.target_path)]

    num = len(profiles)

    def resolve_single(single_input):
        i = single_input[0]
        target_path = single_input[1]
        load_json_path = os.path.join(target_path, "load.json")
        ld = Load()
        ld.from_json(open(load_json_path, "r").read())
        print("[{}/{}] {}".format(i + 1, num, ld.target))

        dependencies = get_all_dependencies(target_path)
        dicts = make_dicts(target_path, dependencies)

        resolver = FQCNResolver(dicts=dicts)

        plays_path = os.path.join(target_path, "plays.json")
        plays = ObjectList().from_json(fpath=plays_path)
        plays.resolve(resolver)
        plays.dump(fpath=plays_path)

        tasks_path = os.path.join(target_path, "tasks.json")
        tasks = ObjectList().from_json(fpath=tasks_path)
        tasks.resolve(resolver)
        tasks.dump(fpath=tasks_path)

    parallel_input_list = [
        (i, target_path) for i, (target_path) in enumerate(profiles)
    ]

    _ = joblib.Parallel(n_jobs=-1)(
        joblib.delayed(resolve_single)(single_input)
        for single_input in parallel_input_list
    )


if __name__ == "__main__":
    main()
