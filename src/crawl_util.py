import os
import sys
import json
import logging
import subprocess
import tempfile
import shutil
import copy
import yaml

from subprocess import PIPE

from struct5 import Collection, Load, LoadType
from loader import detect_target_type, supported_target_types, get_loader_version, create_load_json_path, get_target_name
from parser import load_name2target_name, Parser
from tree import TreeLoader, TreeNode, load_node_objects, load_tree_json
from variable_resolver import tree_to_task_list, resolve_variables


def create_load_files(is_ext, target_type, target_path_list, output_path):

    profiles = [(target_path) for target_path in target_path_list]

    num = len(profiles)
    if num == 0:
        logging.info("no target dirs found. exitting.")
        sys.exit()
    else:
        logging.info("start loading {} {}(s)".format(num, target_type))

    loader_version = get_loader_version()

    for i, (target_path) in enumerate(profiles):

        target_name = get_target_name(target_type, target_path)
        if is_ext:
            load_json_path = create_load_json_path(target_type, target_name, output_path)
        else:
            load_json_path = output_path

        print("[{}/{}] {} {}       ".format(i+1, num, target_type, target_name))

        if not os.path.exists(target_path):
            raise ValueError("No such file or directory: {}".format(target_path))
        load_json_dir = os.path.dirname(load_json_path)
        if not os.path.exists(load_json_dir):
            os.makedirs(load_json_dir, exist_ok=True)
        print("target_name", target_name)
        print("target_type", target_type)
        print("path", target_path)
        print("loader_version", loader_version)
        print("output_path", load_json_path)
        l = Load(target_name=target_name, target_type=target_type, path=target_path, loader_version=loader_version)
        l.run(output_path=load_json_path)

def create_index_data(is_ext, target_type, target_path_list, src_dir, collection_search_path, output_path):

    index_data = {
        "in_path": src_dir,
        "out_path": output_path,
        "collection_path": collection_search_path,
        "mode": "ext" if is_ext else "root",
        "target_type": target_type,
        "generated_load_files": [],
        "dep_collection_load_files": [],
    }

    profiles = [(target_path) for target_path in target_path_list]

    generated_load_files = []
    if is_ext:

        for target_path in profiles:
            target_name = get_target_name(target_type, target_path)
            load_json_path = create_load_json_path(target_type, target_name, output_path)
            lf = load_json_path.replace(output_path, "")
            if lf.startswith("/"):
                lf = lf[1:]
            generated_load_files.append({
                "file": lf,
                "name": target_name,
                "type": target_type,
            })
    else:
        generated_load_files = [{
            "file": output_path,
            "name": "",
            "type": ""
            }]
    index_data["generated_load_files"] = generated_load_files

    dep_collection_load_files = []
    if target_type == LoadType.ROLE_TYPE:
        dep_collection_load_files = find_load_files_for_dependency_collections(target_path_list, collection_search_path)
        index_data["dep_collection_load_files"] = dep_collection_load_files

    return index_data

def find_load_files_for_dependency_collections(role_path_list, collection_search_path):
    dep_collections = []
    for role_path in role_path_list:
        _metadata_path_cand1 = os.path.join(role_path, "meta/main.yml")
        _metadata_path_cand2 = os.path.join(role_path, "meta/main.yaml")
        metadata_path = ""
        if os.path.exists(_metadata_path_cand1):
            metadata_path = _metadata_path_cand1
        elif os.path.exists(_metadata_path_cand2):
            metadata_path = _metadata_path_cand2
        if metadata_path == "":
            continue
        metadata = {}
        try:
            metadata = yaml.safe_load(open(metadata_path, "r"))
        except:
            pass
        dep_collection_key = "collections"
        if dep_collection_key not in metadata:
            continue
        dep_collections_in_this_role = metadata.get(dep_collection_key, [])
        if not isinstance(dep_collections_in_this_role, list):
            continue
        dep_collections.extend(dep_collections_in_this_role)
    load_files = []
    for dep_collection in dep_collections:
        if not isinstance(dep_collection, str):
            continue
        collection_name = dep_collection
        index_file = os.path.join(collection_search_path, "collection-{}-index-ext.json".format(collection_name))
        if not os.path.exists(index_file):
            continue
        index_data = json.load(open(index_file, "r"))
        _load_files_for_this_collection = index_data.get("generated_load_files", [])
        for load_data in _load_files_for_this_collection:
            load_path = load_data.get("file", "")
            already_included = len([True for l in load_files if l.get("file", "") == load_path]) > 0
            if load_path != "" and not already_included:
                load_files.append(load_data)
    return load_files

def load_definitions(is_ext, index_path, load_path, output_path):

    load_json_path_list = []
    if index_path != "":
        if os.path.isfile(index_path):
            with open(index_path, "r") as file:
                index_data = json.load(file)
                load_dir = index_data.get("out_path", "")
                load_json_name_list = index_data.get("generated_load_files", [])
                load_json_path_list = [os.path.join(load_dir, f["file"]) for f in load_json_name_list]
        else:
            files = os.listdir(index_path)
            index_json_path_list = [os.path.join(index_path, fname) for fname in files if fname.startswith("index-") and fname.endswith(".json")]
            for i in index_json_path_list:
                with open(i, "r") as file:
                    index_data = json.load(file)
                    load_dir = index_data.get("out_path", "")
                    load_json_name_list = index_data.get("generated_load_files", [])
                    tmp_load_json_list = [os.path.join(load_dir, f["file"]) for f in load_json_name_list]
                    for l in tmp_load_json_list:
                        if l not in load_json_path_list:
                            load_json_path_list.append(l)
    elif load_path != "":
        if os.path.isfile(load_path):
            load_json_path_list = [load_path]
        else:
            files = os.listdir(load_path)
            load_json_path_list = [os.path.join(load_path, fname) for fname in files if fname.startswith("load-") and fname.endswith(".json")]

    if len(load_json_path_list) == 0:
        logging.info("no load json files found. exitting.")
        sys.exit()

    profiles = [(load_json_path, os.path.join(output_path, load_name2target_name(load_json_path)) if is_ext else output_path) for load_json_path in load_json_path_list]

    num = len(profiles)
    if num == 0:
        logging.info("no load json files found. exitting.")
        sys.exit()
    else:
        logging.info("start parsing {} target(s)".format(num))

    p = Parser()
    for i, (load_json_path, output_dir) in enumerate(profiles):
        print("[{}/{}] {}       ".format(i+1, num, load_json_path))
        p.run(load_json_path=load_json_path, output_dir=output_dir)

def install_target(target, target_type, output_dir):
    if target_type != "collection" and target_type != "role":
        raise ValueError("Invalid target_type: {}".format(target_type))
    proc = subprocess.run("ansible-galaxy {} install {} -p {}".format(target_type, target, output_dir), shell=True, stdout=PIPE, stderr=PIPE, text=True)
    install_msg = proc.stdout
    print('STDOUT: {}'.format(install_msg))
    return proc.stdout

def move_index(path1, path2, params):
    with open(path1, "r") as f1:
        js1 = json.load(f1)
        js2 = copy.deepcopy(js1)
        if any(params):
            for p in params:
                js2[p] = params[p]
        with open(path2, "w") as f2:
            json.dump(js2, f2)

def move_load_file(path1, src1, path2, src2):

    if os.path.exists(path2) and os.path.isdir(path2):
        raise ValueError("{} is not file".format(path2))

    js2 = None
    p1 = None
    p2 = None
    with open(path1, "r") as f1:
        js1 = json.load(f1)
        js2 = copy.deepcopy(js1)
        p1 = js1.get("path","")
        p2 = p1.replace(src1, src2, 1)
        js2["path"] = p2

    if src1 != src2:

        if os.path.exists(p2):
            if os.path.isfile(p2):
                raise ValueError("{} is not directory".format(p2))
        else:
            os.makedirs(p2)

        def copytree(src,dst):
            if src == "" or not os.path.exists(src) or not os.path.isdir(src):
                raise ValueError("src {} is not directory".format(src))
            if dst == "" or ".." in dst:
                raise ValueError("dst {} is invalid".format(dst))
            os.system("cp -r {}/ {}/".format(src, dst))

        # use cp instead of shutil.copytree to avoid symlink reference loop
        copytree(p1, p2)

    with open(path2, "w") as f2:
        json.dump(js2, f2)

def move_definitions(dir1, src1, dir2, src2):

    if not os.path.exists(dir2):
        os.makedirs(dir2)
    if not os.path.isdir(dir2):
        raise ValueError("{} is not directory".format(dir2))

    if not os.path.exists(dir1) or not os.path.isdir(dir1):
        raise ValueError("{} is invalid definition directory".format(dir1))

    js2 = None
    map1 = os.path.join(dir1, "mappings.json")
    with open(map1, "r") as f1:
        js1 = json.load(f1)
        js2 = copy.deepcopy(js1)
        p1 = js1.get("path","")
        p2 = p1.replace(src1, src2, 1)
        js2["path"] = p2

    if os.path.exists(dir2):
        shutil.rmtree(dir2)
    shutil.copytree(dir1, dir2, dirs_exist_ok=True)
    map2 = os.path.join(dir2, "mappings.json")
    with open(map2, "w") as f2:
        json.dump(js2, f2)

def crawl_ext(target, target_type, dst_dir, collection_search_path, skip_install):

    if dst_dir == "":
        raise ValueError("common_data_dir must be specified")

    is_ext = True

    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)

    _params_after = None

    with tempfile.TemporaryDirectory() as tmpdir:

        dst_src_dir = os.path.join(dst_dir, "src")
        if not os.path.exists(dst_src_dir):
            os.makedirs(dst_src_dir)

        dst_load_files_dir = os.path.join(dst_dir, "ext")
        if not os.path.exists(dst_load_files_dir):
            os.makedirs(dst_load_files_dir)

        dst_install_log = os.path.join(dst_dir, "{}-{}-install.log".format(target_type, target))
        dst_index_file = os.path.join(dst_dir, "{}-{}-index-ext.json".format(target_type, target))

        tmp_load_files_dir = os.path.join(tmpdir, "ext") if not skip_install else dst_load_files_dir
        tmp_index_file = os.path.join(tmpdir, "index-ext.json") if not skip_install else dst_index_file
        tmp_install_log = os.path.join(tmpdir, "install.log")
        tmp_defs_dir = os.path.join(tmpdir, "definitions")
        tmp_src_dir = os.path.join(tmpdir, "src") if not skip_install else dst_src_dir

        print("temporary dir {} created".format(tmpdir))

        _params_before = {
            "is_ext": True,
            "target": target,
            "target_type": target_type,
            "load_files_dir": tmp_load_files_dir,
            "index_file": tmp_index_file,
            "install_log": tmp_install_log,
            "defs_dir" : tmp_defs_dir,
            "src_dir": tmp_src_dir
        }

        print("before move")
        print(json.dumps(_params_before, indent=2))

        if skip_install:
            tmp_src_dir = dst_src_dir
        else:
            # ansible-galaxy install
            print("installing a {} <{}> from galaxy".format(target_type, target))
            install_msg = install_target(target, target_type, tmp_src_dir)
            with open(tmp_install_log, "w") as f:
                print(install_msg, file=f)
                print(install_msg)

        # load src, create load.json
        print("crawl content")

        if skip_install:
            target_path_list = []
            if not os.path.exists(tmp_index_file):
                raise ValueError("No index file {}".format(tmp_index_file))
            with open(tmp_index_file, "r") as f:
                index_data = json.load(f)
                _load_files_for_this_collection = index_data.get("generated_load_files", [])
                if target_type == LoadType.COLLECTION_TYPE:
                    in_path = index_data.get("in_path", "")
                    for load_data in _load_files_for_this_collection:
                        name = load_data.get("name", "")
                        if name != "":
                            name_arr = name.split(".")
                            load_path = os.path.join(in_path, "ansible_collections")
                            for v in name_arr:
                                load_path = os.path.join(load_path, v)
                            print("load_path", load_path)
                            target_path_list.append(load_path)
                elif target_type == LoadType.ROLE_TYPE:
                    in_path = index_data.get("in_path", "")
                    for load_data in _load_files_for_this_collection:
                        name = load_data.get("name", "")
                        if name != "":
                            load_path = os.path.join(in_path, name)
                            target_path_list.append(load_path)
                else:
                    raise ValueError("Unsupported target type")

        else:
            _, target_path_list = detect_target_type(tmp_src_dir, is_ext)

            logging.info("the detected target type: \"{}\", found targets: {}".format(target_type, len(target_path_list)))
            if target_type not in supported_target_types:
                logging.error("this target type is not supported")
                sys.exit(1)

        create_load_files(is_ext, target_type, target_path_list, tmp_load_files_dir)

        if not skip_install:
            index_data = create_index_data(is_ext, target_type, target_path_list, tmp_src_dir, collection_search_path, tmp_load_files_dir)
            with open(tmp_index_file, "w") as file:
                json.dump(index_data, file)

        # decompose files to definitions
        print("decomposing files")
        load_definitions(is_ext, tmp_index_file, "", tmp_defs_dir)

        # move the files to common dir
        with open(tmp_index_file, "r") as f:
            index_data = json.load(f)
            defined_load_files_dir = index_data.get("out_path","")
            defined_generated_load_files = index_data.get("generated_load_files",[])
            if defined_load_files_dir == "":
                raise ValueError("no out_path in index file")

        print("moving load files to common dir")
        for v in defined_generated_load_files:
            defined_load_file = v["file"]
            target_name = v["name"]
            target_type = v["type"]
            defined_load_file_path = os.path.join(defined_load_files_dir, defined_load_file)
            dst_load_file_path = os.path.join(dst_load_files_dir, defined_load_file)
            move_load_file(defined_load_file_path, tmp_src_dir, dst_load_file_path, dst_src_dir)

        if not skip_install:
            print("moving index")
            params = {
                "in_path": dst_src_dir,
                "out_path": dst_load_files_dir,
            }
            move_index(tmp_index_file, dst_index_file, params)

            print("moving install log")
            shutil.move(tmp_install_log, dst_install_log)


        print("moving load definitions to common dir")
        dst_defs_dir = os.path.join(dst_dir, "definitions")
        if not os.path.exists(dst_defs_dir):
            os.makedirs(dst_defs_dir)
        for v in defined_generated_load_files:
            target_name = v["name"]
            target_type = v["type"]
            def1 = os.path.join(tmp_defs_dir, "{}-{}".format(target_type, target_name))
            def2 = os.path.join(dst_defs_dir, "{}-{}".format(target_type, target_name))
            move_definitions(def1, tmp_src_dir, def2, dst_src_dir)

        _params_after = {
            "is_ext": True,
            "target": target,
            "target_type": target_type,
            "load_files_dir": dst_load_files_dir,
            "index_file": dst_index_file,
            "install_log": dst_install_log,
            "defs_dir" : dst_defs_dir,
            "src_dir": dst_src_dir
        }

        print("after move")
        print(json.dumps(_params_after, indent=2))

    if not os.path.exists(tmpdir):
        print("temporary dir {} cleared".format(tmpdir))
    else:
        print("temporary dir {} remaining somehow...".format(tmpdir))


    return _params_after

def crawl_root(target, target_type, src_index_file, output_dir):

    is_ext = False

    src_load_file = None
    with open(src_index_file, "r") as f:
        src_index = json.load(f)
        src_load_dir = src_index.get("out_path", "")
        for v in src_index.get("generated_load_files", []):
            if v["name"] == target and v["type"] == target_type:
                src_load_file = os.path.join(src_load_dir, v["file"])

    if src_load_file:
        with open(src_load_file, "r") as f:
            src_load = json.load(f)
            src_dir = src_load.get("path", "")

    dst_dir = os.path.join(output_dir, "root")
    if not os.path.exists(dst_dir):
        os.makedirs(dst_dir)


    _params_after = None


    with tempfile.TemporaryDirectory() as tmpdir:

        tmp_load_file = os.path.join(tmpdir, "load-root.json")
        tmp_defs_dir = os.path.join(tmpdir, "definitions")

        print("temporary dir {} created".format(tmpdir))

        _params_before = {
            "is_ext": is_ext,
            "target": target,
            "target_type": target_type,
            "load_file": tmp_load_file,
            "defs_dir" : tmp_defs_dir,
            "src_dir": src_dir
        }

        print("before move")
        print(json.dumps(_params_before, indent=2))

        # ansible-galaxy install
        # load src, create load.json
        print("crawl content")

        target_type, target_path_list = detect_target_type(src_dir, is_ext)

        logging.info("the detected target type: \"{}\", found targets: {}".format(target_type, len(target_path_list)))
        if target_type not in supported_target_types:
            logging.error("this target type is not supported")
            sys.exit(1)

        create_load_files(is_ext, target_type, target_path_list, tmp_load_file)

        # load index_
        print("decomposing files")
        load_definitions(is_ext, "", tmp_load_file, tmp_defs_dir)

        # move the files to common dir

        dst_load_file = os.path.join(dst_dir, "{}-{}-load-root.json".format(target_type, target))

        print("moving load file")
        move_load_file(tmp_load_file, src_dir, dst_load_file, src_dir)

        print("moving results to common dir")
        dst_def_dir = os.path.join(dst_dir, "definitions", target_type, target)
        if not os.path.exists(dst_def_dir):
            os.makedirs(dst_def_dir)

        move_definitions(tmp_defs_dir, src_dir, dst_def_dir, src_dir)

        _params_after = {
            "is_ext": is_ext,
            "target": target,
            "target_type": target_type,
            "load_file": dst_load_file,
            "defs_dir" : dst_def_dir,
            "src_dir": src_dir
        }

        print("after move")
        print(json.dumps(_params_after, indent=2))

    if not os.path.exists(tmpdir):
        print("temporary dir {} cleared".format(tmpdir))
    else:
        print("temporary dir {} remaining somehow...".format(tmpdir))

    return _params_after

def tree(root_def_dir, ext_def_dir, index_path, out_dir):
    dst_tree_path = os.path.join(out_dir, "tree.json")
    dst_node_path = os.path.join(out_dir, "node_objects.json")
    trees = None
    node_objects = None
    with tempfile.TemporaryDirectory() as tmpdirname:
        tree_path = os.path.join(tmpdirname, "tree.json")
        node_path = os.path.join(tmpdirname, "node_objects.json")
        tl = TreeLoader(root_def_dir, ext_def_dir, index_path, tree_path, node_path)
        tl.run()
        trees = load_tree_json(tree_path)
        node_objects = load_node_objects(node_path)

        if trees is None:
            raise ValueError("failed to get trees")
        if node_objects is None:
            raise ValueError("failed to get node_objects")


        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        shutil.move(tree_path, dst_tree_path)
        shutil.move(node_path, dst_node_path)

    return dst_tree_path, dst_node_path

def resolve(tree_path, node_path, out_dir):
    trees = load_tree_json(tree_path)
    node_objects = load_node_objects(node_path)

    tasks_r_lines = []
    for tree in trees:
        if not isinstance(tree, TreeNode):
            continue
        tasks = tree_to_task_list(tree, node_objects)
        d = {
            "root_key": tree.key,
            "tasks": tasks,
        }
        line = json.dumps(d)
        tasks_r_lines.append(line)
    tasks_r_path = os.path.join(out_dir, "tasks_r.json")
    open(tasks_r_path, "w").write("\n".join(tasks_r_lines))


    tasks_rv_lines = []
    for tree in trees:
        if not isinstance(tree, TreeNode):
            continue
        tasks = resolve_variables(tree, node_objects)
        d = {
            "root_key": tree.key,
            "tasks": tasks,
        }
        line = json.dumps(d)
        tasks_rv_lines.append(line)
    tasks_rv_path = os.path.join(out_dir, "tasks_rv.json")
    open(tasks_rv_path, "w").write("\n".join(tasks_rv_lines))



    
