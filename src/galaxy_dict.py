import argparse
import os
import json
import jsonpickle
import logging
from struct4 import get_object, Module, Task, TaskFile, Role, Playbook, Play, Collection


class GalaxyDict():
    def __init__(self, mode="load", dir="", target="", fqcn_to_extract="", out_dir=""):
        available_modes = ["load", "dict1", "dict2", "merge", "extract"]
        if mode not in available_modes:
            raise ValueError("mode must be one of \"{}\"".format(available_modes))
        if mode == "load" and target not in ["role", "collection"]:
            raise ValueError("target must be either \"role\" or \"collection\" in \"load\" mode")
        self.mode = mode
        self.dir = dir
        self.target = target
        self.fqcn_to_extract = fqcn_to_extract
        self.json_search_root = "/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/galaxy_resolved"
        self.out_dir = out_dir

        self.dict1_path = "/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/dict1.json"
        self.dict2_path = "/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-experiments/dict2.json"
        
        with open(self.dict1_path, "r") as file:
            d = json.load(file)
            self.module_dict = d.get("module", {})
            self.taskfile_dict = d.get("taskfile", {})
            self.role_dict = d.get("role", {})
        with open(self.dict2_path, "r") as file:
            d = json.load(file)
            self.task_dict = d.get("task", {})
            self.playbook_dict = d.get("playbook", {})

        self.json_cache = {}

    def run(self):
        if self.mode == "load":
            self.load()
        elif self.mode == "dict1":
            self.dict_one()
        elif self.mode == "dict2":
            self.dict_two()
        elif self.mode == "merge":
            self.merge()
        elif self.mode == "extract":
            self.extract()
        return

    def load(self):
        if self.target == "role":
            self.load_roles()
        elif self.target == "collection":
            self.load_collections()
        return

    def load_roles(self):
        dirs = os.listdir(self.dir)
        for d in dirs:
            role_dir_path = os.path.join(self.dir, d)
            r = Role()
            try:
                r.load(path=role_dir_path, basedir=self.dir)
            except:
                logging.warning("error when loading a Role at {}".format(role_dir_path))
                continue
            outfile = os.path.join(self.out_dir, "role-{}.json".format(r.name))
            with open(outfile, "w") as file:
                file.write(r.dump())
        
    def load_collections(self):
        dirs = os.listdir(self.dir)
        base_dir = self.dir
        if base_dir.endswith("/"):
            base_dir = base_dir[:-1]
        base_dir = os.path.dirname(base_dir)
        for d in dirs:
            coll_dir_path = os.path.join(self.dir, d)
            c = Collection()
            try:
                c.load(collection_dir=coll_dir_path, basedir=base_dir)
            except:
                logging.warning("error when loading a Collection at {}".format(coll_dir_path))
                continue
            outfile = os.path.join(self.out_dir, "collection-{}.json".format(c.name))
            with open(outfile, "w") as file:
                file.write(c.dump())

    def dict_one(self):
        path = self.dir
        filename = os.path.basename(path)
        json_str = ""
        d = {
            "module": {},
            "taskfile": {},
            "role": {},
        }
        with open(path, "r") as file:
            json_str = file.read()
        if filename.startswith("role-"):
            r = Role()
            r.from_json(json_str)
            d = role_to_dict_one(r, filename)
        elif filename.startswith("collection-"):
            c = Collection()
            c.from_json(json_str)
            d = collection_to_dict_one(c, filename)
        out_json = json.dumps(d)
        outfile = os.path.join(self.out_dir, filename)
        with open(outfile, "w") as file:
            file.write(out_json)

    def dict_two(self):
        path = self.dir
        filename = os.path.basename(path)
        json_str = ""
        d = {
            "task": {},
            "playbook": {},
        }
        with open(path, "r") as file:
            json_str = file.read()
        if filename.startswith("role-"):
            r = Role()
            r.from_json(json_str)
            d = role_to_dict_two(r, filename)
        elif filename.startswith("collection-"):
            c = Collection()
            c.from_json(json_str)
            d = collection_to_dict_two(c, filename)
        out_json = json.dumps(d)
        outfile = os.path.join(self.out_dir, filename)
        with open(outfile, "w") as file:
            file.write(out_json)

    def merge(self):
        d = {}
        files = [f for f in os.listdir(self.dir) if f.endswith(".json")]
        num = len(files)
        for i, f in enumerate(files):
            print("\r[{}/{}] {}   ".format(i, num, f), end="")
            fpath = os.path.join(self.dir, f)
            di = json.load(open(fpath, "r"))
            merge_dict(d, di)
        print("\ndump dict json")
        with open(self.out_dir, "w") as file:
            file.write(json.dumps(d))
        print("done")
        return

    def extract(self):
        supported = ["playbook"]
        if self.target not in supported:
            raise ValueError("the specified target is not supported yet")
        obj_dict = {}
        if self.target == "playbook":
            obj_dict = self.playbook_dict
        if len(obj_dict) == 0:
            raise ValueError("found dict has 0 data; something wrong")
        found = []
        num = len(obj_dict)
        for i, (k, v) in enumerate(obj_dict.items()):
            print("\r[{}/{}] {}".format(i+1, num, k), end="")
            obj_name = k
            if obj_name == "":
                continue
            base_json_path = v.get("path", "")
            if base_json_path == "":
                continue
            json_path = os.path.join(self.json_search_root, base_json_path)
            obj = get_object(json_path, self.target, obj_name, self.json_cache)
            use_the_module = False
            try:
                use_the_module = self.use_module(obj, self.fqcn_to_extract)
            except Exception as e:
                logging.warning("error while use_module() for {}: {}".format(obj_name, e.args[0]))
            if use_the_module:
                found.append(obj)
        json_str = jsonpickle.encode(found, make_refs=False)
        with open(self.out_dir, "w") as file:
            file.write(json_str)

    def use_module(self, obj, module_fqcn, ancestor_tasks=[]):
        ancestors = [task_id for task_id in ancestor_tasks]
        if isinstance(obj, Playbook):
            if "plays" in obj.__dict__:
                for p in obj.plays:
                    if self.use_module(p, module_fqcn, ancestors):
                        return True
            else:
                for t in obj.tasks:
                    if self.use_module(t, module_fqcn, ancestors):
                        if t.id in ancestors:
                            return False
                        return True
                for rip in obj.roles:
                    if rip.resolved_name == "":
                        continue
                    found_role = self.role_dict.get(rip.resolved_name, None)
                    if found_role is None:
                        continue
                    base_json_path = found_role.get("path", "")
                    if base_json_path == "":
                        continue
                    json_path = os.path.join(self.json_search_root, base_json_path)
                    r = get_object(json_path, "role", rip.resolved_name, self.json_cache)
                    if self.use_module(r, module_fqcn, ancestors):
                        return True
        elif isinstance(obj, Play):
            for t in obj.pre_tasks:
                if t.id in ancestors:
                    return False
                if self.use_module(t, module_fqcn, ancestors):
                    return True
            for t in obj.tasks:
                if t.id in ancestors:
                    return False
                if self.use_module(t, module_fqcn, ancestors):
                    return True
            for rip in obj.roles:
                if rip.resolved_name == "":
                    continue
                found_role = self.role_dict.get(rip.resolved_name, None)
                if found_role is None:
                    continue
                base_json_path = found_role.get("path", "")
                if base_json_path == "":
                    continue
                json_path = os.path.join(self.json_search_root, base_json_path)
                r = get_object(json_path, "role", rip.resolved_name, self.json_cache)
                if self.use_module(r, module_fqcn, ancestors):
                    return True
        elif isinstance(obj, Task):
            ancestors.append(obj.id)
            if obj.resolved_name == "":
                return False
            if obj.executable_type == "Module":
                return obj.resolved_name == module_fqcn
            elif obj.executable_type == "Taskfile":
                found_taskfile = self.taskfile_dict.get(obj.resolved_name, None)
                if found_taskfile is None:
                    return False
                base_json_path = found_taskfile.get("path", "")
                if base_json_path == "":
                    return False
                json_path = os.path.join(self.json_search_root, base_json_path)
                tf = get_object(json_path, "taskfile", obj.resolved_name, self.json_cache)
                for t in tf.tasks:
                    if t.id in ancestors:
                        return False
                    if self.use_module(t, module_fqcn, ancestors):
                        return True
            elif obj.executable_type == "Role":
                found_role = self.role_dict.get(obj.resolved_name, None)
                if found_role is None:
                    return False
                base_json_path = found_role.get("path", "")
                if base_json_path == "":
                    return False
                json_path = os.path.join(self.json_search_root, base_json_path)
                r = get_object(json_path, "role", obj.resolved_name, self.json_cache)
                if self.use_module(r, module_fqcn, ancestors):
                    return True
        elif isinstance(obj, Role):
            for tf in obj.taskfiles:
                 for t in tf.tasks:
                    if t.id in ancestors:
                        return False
                    if self.use_module(t, module_fqcn, ancestors):
                        return True
        return False
        
def merge_dict(d, di):
    for k in di:
        dk = d.get(k, {})
        dk.update(di[k])
        d[k] = dk
    return

def role_to_dict_one(role, json_path=""):
    if not isinstance(role, Role):
        raise ValueError("this is not a Role but {}".format(type(role).__name__))
    
    module_list = [module_to_dict_item(m, json_path=json_path) for m in role.modules]
    module_key_list = [d[0] for d in module_list]
    module_val_list = [d[1] for d in module_list]
    module_dict = dict(zip(module_key_list, module_val_list))
    
    taskfile_list = [taskfile_to_dict_item(tf, json_path=json_path) for tf in role.taskfiles]
    taskfile_key_list = [d[0] for d in taskfile_list]
    taskfile_val_list = [d[1] for d in taskfile_list]
    taskfile_dict = dict(zip(taskfile_key_list, taskfile_val_list))

    k, v = role_to_dict_item(role, json_path=json_path)
    role_dict = {k: v}

    dict_one = {
        "module": module_dict,
        "taskfile": taskfile_dict,
        "role": role_dict,
    }
    return dict_one


def role_to_dict_two(role, json_path=""):
    if not isinstance(role, Role):
        raise ValueError("this is not a Role but {}".format(type(role).__name__))
    
    task_list = [task_to_dict_item(t, json_path=json_path) for tf in role.taskfiles for t in tf.tasks]
    task_key_list = [d[0] for d in task_list]
    task_val_list = [d[1] for d in task_list]
    task_dict = dict(zip(task_key_list, task_val_list))

    playbook_dict = {}

    dict_one = {
        "task": task_dict,
        "playbook": playbook_dict,
    }
    return dict_one

def collection_to_dict_one(collection, json_path=""):
    if not isinstance(collection, Collection):
        raise ValueError("this is not a Collection but {}".format(type(collection).__name__))
    
    module_list = [module_to_dict_item(m, json_path=json_path) for m in collection.modules]
    module_key_list = [d[0] for d in module_list]
    module_val_list = [d[1] for d in module_list]

    module_in_role_list = [module_to_dict_item(m, json_path=json_path) for r in collection.roles for m in r.modules]
    module_in_role_key_list = [d[0] for d in module_in_role_list]
    module_in_role_val_list = [d[1] for d in module_in_role_list]
    module_key_list.extend(module_in_role_key_list)
    module_val_list.extend(module_in_role_val_list)

    module_dict = dict(zip(module_key_list, module_val_list))
    
    taskfile_list = [taskfile_to_dict_item(tf, json_path=json_path) for tf in collection.taskfiles]
    taskfile_key_list = [d[0] for d in taskfile_list]
    taskfile_val_list = [d[1] for d in taskfile_list]

    taskfile_in_role_list = [taskfile_to_dict_item(tf, json_path=json_path) for r in collection.roles for tf in r.taskfiles]
    taskfile_in_role_key_list = [d[0] for d in taskfile_in_role_list]
    taskfile_in_role_val_list = [d[1] for d in taskfile_in_role_list]
    taskfile_key_list.extend(taskfile_in_role_key_list)
    taskfile_val_list.extend(taskfile_in_role_val_list)

    taskfile_dict = dict(zip(taskfile_key_list, taskfile_val_list))

    role_list = [role_to_dict_item(r, json_path=json_path) for r in collection.roles]
    role_key_list = [d[0] for d in role_list]
    role_val_list = [d[1] for d in role_list]
    role_dict = dict(zip(role_key_list, role_val_list))

    dict_one = {
        "module": module_dict,
        "taskfile": taskfile_dict,
        "role": role_dict,
    }
    return dict_one

def collection_to_dict_two(collection, json_path=""):
    if not isinstance(collection, Collection):
        raise ValueError("this is not a Collection but {}".format(type(collection).__name__))
    
    task_list = [task_to_dict_item(t, json_path=json_path) for tf in collection.taskfiles for t in tf.tasks]
    task_key_list = [d[0] for d in task_list]
    task_val_list = [d[1] for d in task_list]

    task_in_playbook_pre_list = [task_to_dict_item(t, json_path=json_path) for pb in collection.playbooks for p in pb.plays for t in p.pre_tasks]
    task_in_playbook_pre_key_list = [d[0] for d in task_in_playbook_pre_list]
    task_in_playbook_pre_val_list = [d[1] for d in task_in_playbook_pre_list]
    task_key_list.extend(task_in_playbook_pre_key_list)
    task_val_list.extend(task_in_playbook_pre_val_list)

    task_in_playbook_list = [task_to_dict_item(t, json_path=json_path) for pb in collection.playbooks for p in pb.plays for t in p.tasks]
    task_in_playbook_key_list = [d[0] for d in task_in_playbook_list]
    task_in_playbook_val_list = [d[1] for d in task_in_playbook_list]
    task_key_list.extend(task_in_playbook_key_list)
    task_val_list.extend(task_in_playbook_val_list)

    task_in_role_list = [task_to_dict_item(t, json_path=json_path) for r in collection.roles for tf in r.taskfiles for t in tf.tasks]
    task_in_role_key_list = [d[0] for d in task_in_role_list]
    task_in_role_val_list = [d[1] for d in task_in_role_list]
    task_key_list.extend(task_in_role_key_list)
    task_val_list.extend(task_in_role_val_list)

    task_dict = dict(zip(task_key_list, task_val_list))

    playbook_list = [playbook_to_dict_item(p, json_path=json_path) for p in collection.playbooks]
    playbook_key_list = [d[0] for d in playbook_list]
    playbook_val_list = [d[1] for d in playbook_list]
    playbook_dict = dict(zip(playbook_key_list, playbook_val_list))

    dict_one = {
        "task": task_dict,
        "playbook": playbook_dict,
    }
    return dict_one
    

def module_to_dict_item(module, json_path=""):
    if not isinstance(module, Module):
        raise ValueError("this is not a Module but {}".format(type(module).__name__))
    key = module.fqcn
    value = {
        "path": json_path,
        "collection": module.collection,
        "role": module.role,
    }
    return key, value

def task_to_dict_item(task, json_path=""):
    if not isinstance(task, Task):
        raise ValueError("this is not a Task but {}".format(type(task).__name__))
    key = task.id
    value = {
        "path": json_path,
        "collection": task.collection,
        "role": task.role,
        "executable_type": task.executable_type,
        "executable": task.executable,
        "resolved_name": task.resolved_name,
        "defined_in": task.defined_in,
    }
    return key, value

def taskfile_to_dict_item(taskfile, json_path=""):
    if not isinstance(taskfile, TaskFile):
        raise ValueError("this is not a Taskfile but {}".format(type(taskfile).__name__))
    key = taskfile.defined_in
    value = {
        "path": json_path,
        "collection": taskfile.collection,
        "role": taskfile.role,
    }
    return key, value

def role_to_dict_item(role, json_path=""):
    if not isinstance(role, Role):
        raise ValueError("this is not a Role but {}".format(type(role).__name__))
    key = role.fqcn
    value = {
        "path": json_path,
        "collection": role.collection,
    }
    return key, value

def playbook_to_dict_item(playbook, json_path=""):
    if not isinstance(playbook, Playbook):
        raise ValueError("this is not a Playbook but {}".format(type(playbook).__name__))
    key = playbook.defined_in
    value = {
        "path": json_path,
        "collection": playbook.collection,
        "role": playbook.role,
    }
    return key, value

def main():
    parser = argparse.ArgumentParser(
        prog='galaxy_dict.py',
        description='make dictionaries from a specified roles/collections directory and output dict json or merge multiple jsons',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-m', '--mode', default="load", help='mode')
    parser.add_argument('-d', '--dir', default="", help='path to input directory')
    parser.add_argument('-t', '--target', default="", help='role or collection when load mode')
    parser.add_argument('-o', '--out-dir', default="", help='path to the output directory')
    parser.add_argument('--module-fqcn', default="", help='module fqcn to extract target with the fqcn')

    args = parser.parse_args()
    m = GalaxyDict(args.mode, args.dir, args.target, args.module_fqcn, args.out_dir)
    m.run()


if __name__ == "__main__":
    main()