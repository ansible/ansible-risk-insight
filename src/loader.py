from dataclasses import dataclass, field
import argparse
import os
import sys
import pathlib
import json
import jsonpickle
import logging
import git
import datetime
import joblib
from resolver_fqcn import FQCNResolver
from struct5 import Load, get_repo_root

supported_target_types = ["collection", "role", "playbook", "repository"]

skip_files = [".DS_Store"]

search_dirs = [
    "testdata-aa",
    "testdata-ab",
    "testdata-ac",
    "testdata-ad",
    "testdata-ae",
    "testdata-af",
    "testdata-ag-ah",
    "testdata-ai",
    "testdata-aj",
    "testdata-ak",
    "testdata-al",
    "testdata-am",
    "testdata-an",
    "testdata-ao",
    "testdata-ap",
    "testdata-collection"
]

def args2target_info(args):
    if args.role != "":
        return args.role, "role"
    elif args.collection != "":
        return args.collection, "collection"
    elif args.playbook != "":
        return args.playbook, "playbook"
    elif args.scm_repo != "":
        return args.scm_repo, "repository"
    else:
        return "", ""

def path2info(path):
    target_type = ""
    if "testdata-collection/ansible_collections/" in path:
        target_type = "collection"
    elif os.path.exists(os.path.join(path, "MANIFEST.json")):
        target_type = "collection"
    elif "/testdata-a" in path:
        target_type = "role"
    elif os.path.exists(os.path.join(path, "meta/main.yml")):
        target_type = "role"
    elif path.endswith(".yml") or path.endswith(".yaml"):
        target_type = "playbook"
    
    if target_type == "":
        return "", ""

    parts = path.split("/")
    if target_type == "role":
        target = parts[-1]
    elif target_type == "collection":
        target = ".".join(parts[-2:])
    elif target_type == "playbook":
        target = path
    return target, target_type

def get_loader_version():
    script_dir = pathlib.Path(__file__).parent.resolve()
    repo = git.Repo(path=script_dir, search_parent_directories=True)
    sha = repo.head.object.hexsha
    return sha

def check_search_dirs(root_dir):
    if not os.path.exists(root_dir):
        raise ValueError("file not found: {}".format(root_dir))
    for d in search_dirs:
        path = os.path.join(root_dir, d)
        if not os.path.exists(path):
            raise ValueError("file not found: {}".format(path))
    return

def get_base_dir(path):
    basedir = ""
    for d in search_dirs:
        if d in path:
            basedir = path.split(d)[0]
            break
    if basedir != "":
        return basedir
    repo_root = get_repo_root(path)
    if repo_root != "":
        basedir = os.path.dirname(os.path.normpath(repo_root))
    if basedir != "":
        return basedir
    return path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='loader.py',
        description='load collection/role/playbook/repository and make call graph',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--target-path', default="", help='target path')
    parser.add_argument('-a', '--all', action='store_true', help='if True, load all collections and roles')
    parser.add_argument('-o', '--output-path', default="", help='path to output file')  

    args = parser.parse_args()

    profiles = []
    if args.all:
        search_root = args.target_path
        output_root = args.output_path
        check_search_dirs(search_root)
        for d in search_dirs:
            if d == "testdata-collection":
                data_root_dir = os.path.join(search_root, d, "ansible_collections")
                dir_names1 = os.listdir(data_root_dir)
                for d1 in dir_names1:
                    if d1.endswith(".info"):
                        continue
                    if d1 in skip_files:
                        continue
                    dir_names2 = os.listdir(os.path.join(data_root_dir, d1))
                    for d2 in dir_names2:
                        if d2 in skip_files:
                            continue
                        target_path = os.path.join(data_root_dir, d1, d2)
                        output_path = os.path.join(output_root, "collection-{}.{}".format(d1, d2), "load.json")
                        p = (target_path, output_path)
                        profiles.append(p)
            else:
                data_root_dir = os.path.join(search_root, d)
                dir_names1 = os.listdir(data_root_dir)
                for d1 in dir_names1:
                    if d1 in skip_files:
                        continue
                    dir_names2 = os.listdir(os.path.join(data_root_dir, d1))
                    for d2 in dir_names2:
                        if d2 in skip_files:
                            continue
                        target_path = os.path.join(data_root_dir, d1, d2)
                        output_path = os.path.join(output_root, "role-{}".format(d2), "load.json")
                        p = (target_path, output_path)
                        profiles.append(p)
                continue
            
    else:
        p = (args.target_path, args.output_path)
        profiles.append(p)

    num = len(profiles)
    if num == 0:
        logging.info("no target dirs found. exitting.")
        sys.exit()
    else:
        logging.info("start loading for {} collections & roles".format(num))
    
    basedir = get_base_dir(profiles[0][0])
    loader_version = get_loader_version()

    def load_single(single_input):
        i = single_input[0]
        target_path = single_input[1]
        output_path = single_input[2]
        target, target_type = path2info(target_path)
        if os.path.exists(output_path):
            d = json.load(open(output_path, "r"))
            timestamp = d.get("timestamp", "")
            if timestamp != "":
                loaded_time = datetime.datetime.fromisoformat(timestamp)
                now = datetime.datetime.utcnow()
                # if the load data was updated within last 10 minutes, skip it
                if (now - loaded_time).total_seconds() < 60 * 10:
                    print("[{}/{}] SKIP: {} {}       ".format(i+1, num, target_type, target))
                    return
        print("[{}/{}] {} {}       ".format(i+1, num, target_type, target))

        target_path = os.path.normpath(target_path)
        if not os.path.exists(target_path):
            raise ValueError("file not found: {}".format(target_path))
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        l = Load(target=target, target_type=target_type, path=target_path, loader_version=loader_version)
        l.run(basedir=basedir, output_path=output_path)

    parallel_input_list = [(i, target_path, output_path) for i, (target_path, output_path) in enumerate(profiles)]
    _ = joblib.Parallel(n_jobs=-1)(joblib.delayed(load_single)(single_input) for single_input in parallel_input_list)
    
