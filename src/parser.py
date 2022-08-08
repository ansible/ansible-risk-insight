import collections
from dataclasses import dataclass, field
import argparse
import os
import sys
import json
import logging
import copy
import joblib
from resolver_fqcn import FQCNResolver
from struct5 import Module, Task, TaskFile, Role, Playbook, Play, Collection, Repository, Load, BuiltinModuleSet, LoadType


class Parser():
    def run(self, load_json_path="", output_dir=""):
        l = Load()
        if load_json_path != "":
            if not os.path.exists(load_json_path):
                raise ValueError("file not found: {}".format(load_json_path))
            l.from_json(open(load_json_path, "r").read())
        
        collection_name = ""
        role_name = ""
        obj = None
        if l.target_type == LoadType.COLLECTION_TYPE:
            collection_name = l.target_name
            c = Collection()
            try:
                c.load(collection_dir=l.path, basedir=l.path, load_children=False)
            except:
                logging.exception("failed to load the collection {}".format(collection_name))
                return
            obj = c
        elif l.target_type == LoadType.ROLE_TYPE:
            role_name = l.target_name
            r = Role()
            try:
                r.load(path=l.path, basedir=l.path, load_children=False)
            except:
                logging.exception("failed to load the role {}".format(role_name))
                return
            obj = r
        elif l.target_type == LoadType.PROJECT_TYPE:
            repo_name = l.target_name
            repo = Repository()
            try:
                repo.load(path=l.path, basedir=l.path)
            except:
                logging.exception("failed to load the project {}".format(repo_name))
                return
            obj = repo
        elif l.target_type == LoadType.PLAYBOOK_TYPE:
            playbook_name = l.target_name
            p = Playbook()
            try:
                p.load(path=l.path, role_name="", collection_name="", basedir=l.path)
            except:
                logging.exception("failed to load the playbook {}".format(playbook_name))
                return
            obj = p
        else:
            raise ValueError("unsupported type: {}".format(l.target_type))

        mappings = {
            "roles": [],
            "taskfiles": [],
            "modules": [],
            "playbooks": [],
        }
        roles = []
        for role_path in l.roles:
            r = Role()
            try:
                r.load(path=role_path, collection_name=collection_name, basedir=l.path)
            except:
                continue
            roles.append(r)
            mappings["roles"].append([role_path, r.key])

        taskfiles = [tf for r in roles for tf in r.taskfiles]
        for taskfile_path in l.taskfiles:
            tf = TaskFile()
            try:
                tf.load(path=taskfile_path, role_name=role_name, collection_name=collection_name, basedir=l.path)
            except:
                continue
            taskfiles.append(tf)
            mappings["taskfiles"].append([taskfile_path, tf.key])

        playbooks = [p for r in roles for p in r.playbooks]
        for playbook_path in l.playbooks:
            p = Playbook()
            try:
                p.load(path=playbook_path, role_name=role_name, collection_name=collection_name, basedir=l.path)
            except:
                continue
            playbooks.append(p)
            mappings["playbooks"].append([playbook_path, p.key])

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
                m.load(module_file_path=module_path, role_name=role_name, collection_name=collection_name, basedir=l.path)
            except:
                continue
            modules.append(m)
            mappings["modules"].append([module_path, m.key])
        
        # TODO: handle builtin modules while making a tree without adding dummy module objects here
        # modules = add_builtin_modules(modules)

        logging.debug("roles: {}".format(len(roles)))
        logging.debug("taskfiles: {}".format(len(taskfiles)))
        logging.debug("modules: {}".format(len(modules)))
        logging.debug("playbooks: {}".format(len(playbooks)))
        logging.debug("plays: {}".format(len(plays)))
        logging.debug("tasks: {}".format(len(tasks)))
        
        if output_dir == "":
            output_dir = os.path.dirname(load_json_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)

        collections = []
        if l.target_type == LoadType.COLLECTION_TYPE:
            collections = [obj]
        elif l.target_type == LoadType.ROLE_TYPE:
            roles = [obj]
        elif l.target_type == LoadType.PLAYBOOK_TYPE:
            playbooks = [obj]

        if len(collections) > 0:
            dump_object_list(collections, os.path.join(output_dir, "collections.json"))
        if len(roles) > 0:
            dump_object_list(roles, os.path.join(output_dir, "roles.json"))
        if len(taskfiles) > 0:
            dump_object_list(taskfiles, os.path.join(output_dir, "taskfiles.json"))
        if len(modules) > 0:
            dump_object_list(modules, os.path.join(output_dir, "modules.json"))
        if len(playbooks) > 0:
            dump_object_list(playbooks, os.path.join(output_dir, "playbooks.json"))
        if len(plays) > 0:
            dump_object_list(plays, os.path.join(output_dir, "plays.json"))
        if len(tasks) > 0:
            dump_object_list(tasks, os.path.join(output_dir, "tasks.json"))

        # save mappings
        l.roles = mappings["roles"]
        l.taskfiles = mappings["taskfiles"]
        l.playbooks = mappings["playbooks"]
        l.modules = mappings["modules"]
        mapping_path = os.path.join(output_dir, "mappings.json")
        open(mapping_path, "w").write(l.dump())

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

def load_name2target_name(path):
    filename = os.path.basename(path)
    parts = os.path.splitext(filename)
    prefix = "load-"
    target_name = parts[0]
    if target_name.startswith(prefix):
        target_name = target_name[len(prefix):]
    return target_name

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='parser.py',
        description='parse collection/role and its children and output definition json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-l', '--load-path', default="", help='load json path/dir')
    parser.add_argument('-i', '--index-path', default="", help='if specified, load files in this index.json (--load-path will be ignored)')
    parser.add_argument('--root', action='store_true', help='enable this if the target is the root')
    parser.add_argument('--ext', action='store_true', help='enable this if the target is the external dependency(s)')
    parser.add_argument('-o', '--output-dir', default="", help='path to the output dir')
    
    args = parser.parse_args()

    if not args.root and not args.ext:
        logging.error("either \"--root\" or \"--ext\" must be specified")
        sys.exit(1)
    is_ext = args.ext

    if args.load_path == "" and args.index_path == "":
        logging.error("either `--load-path` or `--index-path` is required")
        sys.exit(1)

    if args.root and args.load_path == "":
        logging.error("\"--load-path\" must be specified for \"--root\" mode")
        sys.exit(1)

    if args.root and not os.path.isfile(args.load_path):
        logging.error("\"--load-path\" must be a single .json file for \"--root\" mode")
        sys.exit(1)

    if args.load_path != "" and not os.path.exists(args.load_path):
        logging.error("No such file or directory: {}".format(args.load_path))
        sys.exit(1)

    if args.index_path != "" and not os.path.exists(args.index_path):
        logging.error("No such file or directory: {}".format(args.index_path))
        sys.exit(1)

    load_json_path_list = []
    if args.index_path != "":
        if os.path.isfile(args.index_path):
            with open(args.index_path, "r") as file:
                index_data = json.load(file)
                load_dir = index_data.get("out_path", "")
                load_json_name_list = index_data.get("generated_load_files", [])
                load_json_path_list = [os.path.join(load_dir, f) for f in load_json_name_list]
        else:
            files = os.listdir(args.index_path)
            index_json_path_list = [os.path.join(args.index_path, fname) for fname in files if fname.startswith("index-") and fname.endswith(".json")]
            for i in index_json_path_list:
                with open(i, "r") as file:
                    index_data = json.load(file)
                    load_dir = index_data.get("out_path", "")
                    load_json_name_list = index_data.get("generated_load_files", [])
                    tmp_load_json_list = [os.path.join(load_dir, f) for f in load_json_name_list]
                    for l in tmp_load_json_list:
                        if l not in load_json_path_list:
                            load_json_path_list.append(l)
    elif args.load_path != "":
        if os.path.isfile(args.load_path):
            load_json_path_list = [args.load_path]
        else:
            files = os.listdir(args.load_path)
            load_json_path_list = [os.path.join(args.load_path, fname) for fname in files if fname.startswith("load-") and fname.endswith(".json")]

    if len(load_json_path_list) == 0:
        logging.info("no load json files found. exitting.")
        sys.exit()

    profiles = [(load_json_path, os.path.join(args.output_dir, load_name2target_name(load_json_path)) if is_ext else args.output_dir) for load_json_path in load_json_path_list]

    num = len(profiles)
    if num == 0:
        logging.info("no load json files found. exitting.")
        sys.exit()
    else:
        logging.info("start parsing {} target(s)".format(num))
    
    p = Parser()

    def parse_single(single_input):
        i = single_input[0]
        num = single_input[1]
        load_json_path = single_input[2]
        output_dir = single_input[3]
        print("[{}/{}] {}       ".format(i+1, num, load_json_path))

        p.run(load_json_path=load_json_path, output_dir=output_dir)

    parallel_input_list = [(i, num, load_json_path, output_dir) for i, (load_json_path, output_dir) in enumerate(profiles)]
    _ = joblib.Parallel(n_jobs=-1)(joblib.delayed(parse_single)(single_input) for single_input in parallel_input_list)
    
