import collections
from dataclasses import dataclass, field
import argparse
import os
import sys
import logging
import copy
import joblib
from resolver_fqcn import FQCNResolver
from struct5 import Module, Task, TaskFile, Role, Playbook, Play, Collection, Repository, Load, BuiltinModuleSet


class Parser():
    def run(self, load_json_path="", basedir=""):
        l = Load()
        if load_json_path != "":
            if not os.path.exists(load_json_path):
                raise ValueError("file not found: {}".format(load_json_path))
            l.from_json(open(load_json_path, "r").read())
        
        collection_name = ""
        role_name = ""
        obj = None
        if l.target_type == "collection":
            collection_dir = os.path.join(basedir, l.path)
            collection_name = l.target
            c = Collection()
            try:
                c.load(collection_dir=collection_dir, basedir=basedir, load_children=False)
            except:
                logging.exception("failed to load the collection {}".format(collection_name))
                return
            obj = c
        elif l.target_type == "role":
            role_path = os.path.join(basedir, l.path)
            role_name = l.target
            r = Role()
            try:
                r.load(path=role_path, basedir=basedir, load_children=False)
            except:
                logging.exception("failed to load the role {}".format(role_name))
                return
            obj = r
        elif l.target_type == "playbook":
            playbook_path = os.path.join(basedir, l.path)
            playbook_name = l.target
            p = Playbook()
            try:
                p.load(path=playbook_path, role_name="", collection_name="", basedir=basedir)
            except:
                logging.exception("failed to load the playbook {}".format(playbook_name))
                return
            obj = p
        else:
            raise ValueError("unsupported type: {}".format(l.target_type))

        roles = []
        for role_path in l.roles:
            r = Role()
            try:
                r.load(path=role_path, collection_name=collection_name, basedir=basedir)
            except:
                continue
            roles.append(r)

        taskfiles = [tf for r in roles for tf in r.taskfiles]
        for taskfile_path in l.taskfiles:
            tf = TaskFile()
            try:
                tf.load(path=taskfile_path, role_name=role_name, collection_name=collection_name, basedir=basedir)
            except:
                continue
            taskfiles.append(tf)

        playbooks = [p for r in roles for p in r.playbooks]
        for playbook_path in l.playbooks:
            p = Playbook()
            try:
                p.load(path=playbook_path, role_name=role_name, collection_name=collection_name, basedir=basedir)
            except:
                continue
            playbooks.append(p)

        plays = [play for p in playbooks for play in p.plays]

        tasks = [t for tf in taskfiles for t in tf.tasks]
        pre_tasks_in_plays = [t for p in plays for t in p.pre_tasks]
        tasks_in_plays = [t for p in plays for t in p.tasks]
        post_tasks_in_plays = [t for p in plays for t in p.post_tasks]
        tasks.extend(pre_tasks_in_plays)
        tasks.extend(tasks_in_plays)
        tasks.extend(post_tasks_in_plays)

        modules = [m for r in roles for m in r.modules]
        for module_path in l.modules:
            m = Module()
            try:
                m.load(module_file_path=module_path, role_name=role_name, collection_name=collection_name, basedir=basedir)
            except:
                continue
            modules.append(m)
        modules = add_builtin_modules(modules)

        logging.debug("roles: {}".format(len(roles)))
        logging.debug("taskfiles: {}".format(len(taskfiles)))
        logging.debug("modules: {}".format(len(modules)))
        logging.debug("playbooks: {}".format(len(playbooks)))
        logging.debug("plays: {}".format(len(plays)))
        logging.debug("tasks: {}".format(len(tasks)))
        
        output_dir = os.path.dirname(load_json_path)
        if l.target_type == "collection":
            dump_object_list([obj], os.path.join(output_dir, "collections.json"))
            dump_object_list(roles, os.path.join(output_dir, "roles.json"))
        elif l.target_type == "role":
            dump_object_list([obj], os.path.join(output_dir, "roles.json"))
        elif l.target_type == "playbook":
            dump_object_list(roles, os.path.join(output_dir, "roles.json"))

        dump_object_list(taskfiles, os.path.join(output_dir, "taskfiles.json"))
        dump_object_list(modules, os.path.join(output_dir, "modules.json"))
        dump_object_list(playbooks, os.path.join(output_dir, "playbooks.json"))
        dump_object_list(plays, os.path.join(output_dir, "plays.json"))
        dump_object_list(tasks, os.path.join(output_dir, "tasks.json"))
        return
            
def add_builtin_modules(modules):
    current_modules = [m for m in modules]
    builtin_module_names = BuiltinModuleSet().builtin_modules
    for m_name in builtin_module_names:
        fqcn = "ansible.builtin.{}".format(m_name)
        key = "Module {}".format(fqcn)
        collection = "ansible.builtin"
        m = Module(name=m_name, fqcn=fqcn, key=key, collection=collection, role="", defined_in="", builtin=True)
        current_modules.append(m)
    return current_modules
        
def dump_object_list(obj_list, output_path):
    tmp_obj_list = copy.deepcopy(obj_list)
    lines = []
    for i in range(len(tmp_obj_list)):
        tmp_obj_list[i].children_to_key()
        lines.append(tmp_obj_list[i].dump())
    open(output_path, "w").write("\n".join(lines))
    return

def load_path2info(path):
    parts = path.split("/")
    return parts[-2]

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='parser.py',
        description='parse collection/role and its children and output definition json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-l', '--load-path', default="", help='load json path')
    parser.add_argument('-b', '--base-dir', default="", help='base dir path')
    parser.add_argument('-a', '--all', action='store_true', help='if True, load all collections and roles') 

    args = parser.parse_args()

    profiles = []
    if args.all:
        dirnames = os.listdir(args.load_path)
        for dname in dirnames:
            load_json_path = os.path.join(args.load_path, dname, "load.json")
            if os.path.exists(load_json_path):
                p = (load_json_path)
                profiles.append(p)
    else:
        p = (args.load_path)
        profiles.append(p)

    num = len(profiles)
    if num == 0:
        logging.info("no target dirs found. exitting.")
        sys.exit()
    else:
        logging.info("start loading for {} collections & roles".format(num))
    
    basedir = args.base_dir
    p = Parser()

    def parse_single(single_input):
        i = single_input[0]
        load_json_path = single_input[1]
        target = load_path2info(load_json_path)
        print("[{}/{}] {}       ".format(i+1, num, target))

        p.run(load_json_path=load_json_path, basedir=basedir)

    parallel_input_list = [(i, load_json_path) for i, (load_json_path) in enumerate(profiles)]
    _ = joblib.Parallel(n_jobs=-1)(joblib.delayed(parse_single)(single_input) for single_input in parallel_input_list)
    
