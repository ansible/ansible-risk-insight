from dataclasses import dataclass, field
import argparse
import os
import sys
import pathlib
import json
import jsonpickle
import yaml
import logging
import git
import datetime
import joblib
from resolver_fqcn import FQCNResolver
from struct5 import Load, LoadType
from safe_glob import safe_glob



supported_target_types = [LoadType.PROJECT_TYPE, LoadType.COLLECTION_TYPE, LoadType.ROLE_TYPE, LoadType.PLAYBOOK_TYPE]

collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"

def detect_target_type(path, is_ext):
    if os.path.isfile(path):
        # need further check?
        return LoadType.PLAYBOOK_TYPE, [path]

    if os.path.exists(os.path.join(path, collection_manifest_json)):
        return LoadType.COLLECTION_TYPE, [path]
    if os.path.exists(os.path.join(path, role_meta_main_yml)):
        return LoadType.ROLE_TYPE, [path]
    if is_ext:
        collection_meta_files = safe_glob(os.path.join(path, "**", collection_manifest_json), recursive=True)
        if len(collection_meta_files) > 0:
            collection_path_list = [f.replace("/" + collection_manifest_json, "") for f in collection_meta_files]
            return LoadType.COLLECTION_TYPE, collection_path_list
        role_meta_files = safe_glob(os.path.join(path, "**", role_meta_main_yml), recursive=True)
        if len(role_meta_files) > 0:
            role_path_list = [f.replace("/" + role_meta_main_yml, "") for f in role_meta_files]
            return LoadType.ROLE_TYPE, role_path_list
    else:
        return LoadType.PROJECT_TYPE, [path]
    return LoadType.UNKNOWN_TYPE, []

def get_loader_version():
    script_dir = pathlib.Path(__file__).parent.resolve()
    repo = git.Repo(path=script_dir, search_parent_directories=True)
    sha = repo.head.object.hexsha
    return sha

def create_load_json_path(target_type, target_path, output_dir):
    target_name = ""
    if target_type == LoadType.PROJECT_TYPE:
        project_name = os.path.normpath(target_path).split("/")[-1]
        target_name = project_name
    elif target_type == LoadType.COLLECTION_TYPE:
        meta_file = os.path.join(target_path, collection_manifest_json)
        metadata = {}
        with open(meta_file, "r") as file:
            metadata = json.load(file)
        collection_namespace = metadata.get("collection_info", {}).get("namespace", "")
        collection_name = metadata.get("collection_info", {}).get("name", "")
        target_name = "{}.{}".format(collection_namespace, collection_name)
    elif target_type == LoadType.ROLE_TYPE:
        # any better approach?
        target_name = target_path.split("/")[-1]
    elif target_type == LoadType.PLAYBOOK_TYPE:
        target_name = filepath_to_target_name(target_path)

    load_json_path = os.path.join(output_dir, "load-{}-{}.json".format(target_type, target_name))
    return load_json_path, target_name

def filepath_to_target_name(filepath):
    return filepath.translate(str.maketrans({' ': '___', '/': '---', '.':'_dot_'}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog='loader.py',
        description='load project/collection(s)/role(s)/playbook and make a load json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--target-path', default="", help='target path')
    parser.add_argument('-o', '--output-dir', default="", help='path to output dir')
    parser.add_argument('-i', '--index-path', default="", help='path to the output index.json')
    parser.add_argument('--root', action='store_true', help='enable this if the target is the root')
    parser.add_argument('--ext', action='store_true', help='enable this if the target is the external dependency(s)')

    args = parser.parse_args()

    if not args.root and not args.ext:
        logging.error("either \"--root\" or \"--ext\" must be specified")
        sys.exit(1)
    is_ext = args.ext

    target_type, target_path_list = detect_target_type(args.target_path, is_ext)
    logging.info("the detected target type: \"{}\", found targets: {}".format(target_type, len(target_path_list)))
    if target_type not in supported_target_types:
        logging.error("this target type is not supported")
        sys.exit(1)

    profiles = [(target_path) for target_path in target_path_list]

    num = len(profiles)
    if num == 0:
        logging.info("no target dirs found. exitting.")
        sys.exit()
    else:
        logging.info("start loading {} {}(s)".format(num, target_type))
    
    output_dir = args.output_dir
    loader_version = get_loader_version()

    def load_single(single_input):
        i = single_input[0]
        num = single_input[1]
        target_path = os.path.normpath(single_input[2])
        output_dir = single_input[3]
        loader_version = single_input[4]
        output_path, target_name = create_load_json_path(target_type, target_path, output_dir)
        if os.path.exists(output_path):
            d = json.load(open(output_path, "r"))
            timestamp = d.get("timestamp", "")
            if timestamp != "":
                loaded_time = datetime.datetime.fromisoformat(timestamp)
                now = datetime.datetime.utcnow()
                # if the load data was updated within last 10 minutes, skip it
                if (now - loaded_time).total_seconds() < 60 * 10:
                    print("[{}/{}] SKIP: {} {}       ".format(i+1, num, target_type, target_name))
                    return
        print("[{}/{}] {} {}       ".format(i+1, num, target_type, target_name))

        if not os.path.exists(target_path):
            raise ValueError("No such file or directory: {}".format(target_path))
        output_dir = os.path.dirname(output_path)
        if not os.path.exists(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        l = Load(target_name=target_name, target_type=target_type, path=target_path, loader_version=loader_version)
        l.run(output_path=output_path)

    parallel_input_list = [(i, num, target_path, output_dir, loader_version) for i, (target_path) in enumerate(profiles)]
    _ = joblib.Parallel(n_jobs=-1)(joblib.delayed(load_single)(single_input) for single_input in parallel_input_list)

    if args.index_path != "":
        index_data = {
            "in_dir": args.target_path,
            "out_dir": output_dir,
            "mode": "ext" if is_ext else "root",
            "target_type": target_type,
            "generated_load_files": []
        }
        generated_load_files = []
        for target_path in profiles:
            output_path, _ = create_load_json_path(target_type, target_path, output_dir)
            lf = output_path.replace(output_dir, "")
            if lf.startswith("/"):
                lf = lf[1:]
            generated_load_files.append(lf)
        index_data["generated_load_files"] = generated_load_files
        
        with open(args.index_path, "w") as file:
            json.dump(index_data, file)
        
    
    
