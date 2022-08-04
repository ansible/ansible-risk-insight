import os
import re
import json
import jsonpickle
from git import Repo
import joblib
import tempfile
from struct5 import ObjectList, Role, Collection, Load, Repository
from loader import get_loader_version, get_base_dir
from parser import Parser
from resolver_fqcn import FQCNResolver, make_dicts, get_all_dependencies
from graph import Grapher
from tree import TreeLoader, key_to_file_name, dump_node_objects
from converter1 import convert
import argparse
import logging


class Analyzer():
    def __init__(self, target_path):
        self.target_path = target_path

def get_repo_dependencies(repo_json_path, galaxy_dir=""):
    repo = Repository()
    repo_json_str = open(repo_json_path, "r").read()
    repo.from_json(repo_json_str)
    raw_dependencies = repo.requirements
    dep_roles = []
    for dep in raw_dependencies.get("roles", []):
        if isinstance(dep, str):
            dep_roles.append(dep)
        elif isinstance(dep, dict):
            r_name = dep.get("name", "")
            if r_name != "":
                dep_roles.append(r_name)
    dep_colls = []
    for dep in raw_dependencies.get("collections", []):
        if isinstance(dep, str):
            dep_colls.append(dep)
        elif isinstance(dep, dict):
            c_name = dep.get("name", "")
            if c_name != "":
                dep_colls.append(c_name)
    dependencies = {
        "roles": dep_roles,
        "collections": dep_colls,
    }
    for dep_name in dependencies["roles"]:
        sub_target_path = os.path.join(galaxy_dir, "role-{}".format(dep_name))
        sub_dependencies = get_all_dependencies(target_path=sub_target_path, known_dependencies=dependencies)
        dependencies["roles"].extend(sub_dependencies["roles"])
        dependencies["collections"].extend(sub_dependencies["collections"])
    for dep_name in dependencies["collections"]:
        sub_target_path = os.path.join(galaxy_dir, "collection-{}".format(dep_name))
        sub_dependencies = get_all_dependencies(target_path=sub_target_path, known_dependencies=dependencies)
        dependencies["roles"].extend(sub_dependencies["roles"])
        dependencies["collections"].extend(sub_dependencies["collections"])
    return dependencies

def main():
    parser = argparse.ArgumentParser(
        prog='analyze.py',
        description='analyze playbook',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--target-path', default="", help='path to playbook')
    args = parser.parse_args()

    if not os.path.exists(args.target_path):
        raise ValueError("target path does not exist")

    target_path = args.target_path
    target_type = "playbook"
    loader_version = get_loader_version()
    basedir = get_base_dir(target_path)
    # temp_dir = tempfile.TemporaryDirectory()
    # temp_dir_path = temp_dir.name
    temp_dir_path = "/tmp/test-playbook-analyze"
    print("workspace: ", temp_dir_path)
    load_json_path = os.path.join(temp_dir_path, "load.json")

    # create load.json
    l = Load(target=target_path, target_type=target_type, path=target_path, loader_version=loader_version)
    l.run(basedir=basedir, output_path=load_json_path)

    target_playbook_path = l.path
    target_key = "Playbook {}".format(target_playbook_path)

    # create definitions like playbooks.json, roles.json, taskfiles.json and modules.json
    p = Parser()
    p.run(load_json_path=load_json_path, basedir=basedir)

    # TODO: get dependencies dynamically
    repo_json_path = os.path.join(temp_dir_path, "repository.json")
    galaxy_dir = "/Users/Hirokuni.Kitahara1@ibm.com/dev/ansible/ari-data/data"
    dependencies = get_repo_dependencies(repo_json_path, galaxy_dir=galaxy_dir)

    # resolve FQCN for all tasks
    dicts = make_dicts(target_path=temp_dir_path, dependencies=dependencies, galaxy_dir=galaxy_dir, save_marged=True)
    merged_dir_path = os.path.join(temp_dir_path, "merged")
    resolver = FQCNResolver(dicts=dicts)
    
    plays_path = os.path.join(merged_dir_path, "plays.json")
    plays = ObjectList().from_json(fpath=plays_path)
    plays.resolve(resolver)
    plays.dump(fpath=plays_path)

    tasks_path = os.path.join(merged_dir_path, "tasks.json")
    tasks = ObjectList().from_json(fpath=tasks_path)
    tasks.resolve(resolver)
    tasks.dump(fpath=tasks_path)

    g = Grapher(dir=merged_dir_path)
    g.run()

    graph_path = os.path.join(merged_dir_path, "graph.json")
    tl = TreeLoader(graph_path=graph_path, definition_dir=merged_dir_path)

    tree = tl.make_tree(target_key)
    node_objects = tl.node_objects(tree)

    # dump tree.json
    tree_file = os.path.join(temp_dir_path, key_to_file_name("tree", target_key))
    tree.dump(tree_file)

    # dump nodes.json
    node_file = os.path.join(temp_dir_path, key_to_file_name("node", target_key))
    dump_node_objects(node_objects, node_file)

    t_obj, contexts = convert(target_key, temp_dir_path)
    print(json.dumps(t_obj, indent=2))

    contexts_json_str = jsonpickle.encode(contexts)
    contexts_file = os.path.join(temp_dir_path, key_to_file_name("contexts", target_key))
    open(contexts_file, "w").write(contexts_json_str)

    print("done!")
    

if __name__ == "__main__":
    main()