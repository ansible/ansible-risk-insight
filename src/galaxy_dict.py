import argparse
import os
import json
import logging
from struct4 import Module, Task, TaskFile, Role, Collection


class GalaxyDict():
    def __init__(self, mode="load", dir="", target="", out_dir=""):
        if mode not in ["load", "dict1", "merge"]:
            raise ValueError("mode must be either \"load\" or \"merge\"")
        if mode == "load" and target not in ["role", "collection"]:
            raise ValueError("target must be either \"role\" or \"collection\" in \"load\" mode")
        self.mode = mode
        self.dir = dir
        self.target = target
        self.out_dir = out_dir

    def run(self):
        if self.mode == "load":
            self.load()
        elif self.mode == "dict1":
            self.dict_one()
        elif self.mode == "merge":
            self.merge()
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
    
    taskfile_list = [taskfile_to_dict_item(tf, json_path=json_path) for r in collection.roles for tf in r.taskfiles]
    taskfile_key_list = [d[0] for d in taskfile_list]
    taskfile_val_list = [d[1] for d in taskfile_list]
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

    args = parser.parse_args()
    m = GalaxyDict(args.mode, args.dir, args.target, args.out_dir)
    m.run()


if __name__ == "__main__":
    main()