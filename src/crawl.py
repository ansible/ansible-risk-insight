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
import subprocess
import tempfile
import shutil
import copy

from subprocess import PIPE

from resolver_fqcn import FQCNResolver
from struct5 import Load, LoadType
from safe_glob import safe_glob
from loader import detect_target_type, supported_target_types, get_loader_version, create_load_json_path
from parser import load_name2target_name, Parser

def crawl(is_ext, output_path, index_path, crawl_target_path):
    target_type, target_path_list = detect_target_type(crawl_target_path, is_ext)
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

    loader_version = get_loader_version()

    for i, (target_path) in enumerate(profiles):

        load_json_path = output_path
        target_name = target_path

        if is_ext:
            load_json_path, target_name = create_load_json_path(target_type, target_path, output_path)

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


    if index_path != "":
        index_data = {
            "in_path": crawl_target_path,
            "out_path": output_path,
            "mode": "ext" if is_ext else "root",
            "target_type": target_type,
            "generated_load_files": []
        }

        generated_load_files = []
        if is_ext:

            for target_path in profiles:
                load_json_path, target_name = create_load_json_path(target_type, target_path, output_path)
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

        with open(index_path, "w") as file:
            json.dump(index_data, file)


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
    if target_type != "collection":
        raise ValueError("Invalid target_type: {}".format(target_type))
    proc = subprocess.run("ansible-galaxy {} install {} -p {}".format(target_type, target, output_dir), shell=True, stdout=PIPE, stderr=PIPE, text=True)
    install_msg = proc.stdout
    print('STDOUT: {}'.format(install_msg))
    return proc.stdout

def move_index(path1, path2, params):
    with open(path1, "r") as f1:
        js1 = json.load(f1)
        js2 = copy.deepcopy(js1)
        for p in params:
            js2[p] = params[p]
        with open(path2, "w") as f2:
            json.dump(js2, f2)
    return js1, js2

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

    if os.path.exists(p2):
        if os.path.isfile(p2):
            raise ValueError("{} is not directory".format(p2))
    else:
        os.makedirs(p2)

    shutil.copytree(p1, p2, dirs_exist_ok=True, ignore=shutil.ignore_patterns('.cache'), symlinks=False, ignore_dangling_symlinks=True)
    with open(path2, "w") as f2:
        json.dump(js2, f2)

def move_definitions(dir1, src1, dir2, src2, name, ttype):

    if not os.path.exists(dir2):
        os.makedirs(dir2)
    if not os.path.isdir(dir2):
        raise ValueError("{} is not directory".format(dir2))
    if ttype == "" or name == "":
        raise ValueError("invalid name or type: {}, {}".format(name, ttype))

    def1 = os.path.join(dir1, "{}-{}".format(ttype, name))
    if not os.path.exists(def1) or not os.path.isdir(def1):
        raise ValueError("{} is invalid definition directory".format(def1))

    js2 = None
    map1 = os.path.join(def1, "mappings.json")
    with open(map1, "r") as f1:
        js1 = json.load(f1)
        js2 = copy.deepcopy(js1)
        p1 = js1.get("path","")
        p2 = p1.replace(src1, src2, 1)
        js2["path"] = p2

    def2 = os.path.join(dir2, "{}-{}".format(ttype, name))
    if os.path.exists(def2):
        shutil.rmtree(def2)
    shutil.copytree(def1, def2, dirs_exist_ok=True)
    map2 = os.path.join(def2, "mappings.json")
    with open(map2, "w") as f2:
        json.dump(js2, f2)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='crawl.py',
        description='crawl a collection and store data under a common directory',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-c', '--collection', default="", help='collection name')
    parser.add_argument('-o', '--output-dir', default="", help='path to the output directory')

    args = parser.parse_args()

    if not args.collection:
        logging.error("collection must be specified")
        sys.exit(1)

    if not args.output_dir:
        logging.error("output dir must be specified")
        sys.exit(1)

    _is_ext = True
    _target = args.collection
    _target_type = "collection"
    _common_data_dir = args.output_dir

    # python crawl.py --ext -t $TRIAL_DIR/src -o /tmp/aaaa -i /tmp/index-aaaa/index-ext.json
    # python parser.py --ext -i /tmp/index-aaaa/index-ext.json -o /tmp/bbbb

    _common_src_dir = os.path.join(_common_data_dir, "src")
    _common_ext_dir = os.path.join(_common_data_dir, "ext")
    _common_def_dir = os.path.join(_common_data_dir, "definitions")

    if not os.path.exists(_common_data_dir):
        os.makedirs(_common_data_dir)

    if not os.path.exists(_common_src_dir):
        os.makedirs(_common_src_dir)

    if not os.path.exists(_common_ext_dir):
        os.makedirs(_common_ext_dir)

    if not os.path.exists(_common_def_dir):
        os.makedirs(_common_def_dir)

    with tempfile.TemporaryDirectory() as dname:

        _load_output_path = os.path.join(dname, "ext")
        _load_index_path = os.path.join(dname, "index-ext.json")
        _install_log_path = os.path.join(dname, "install.log")
        _defs_out_path = os.path.join(dname, "definitions")
        # _crawl_target_path = "/tmp/collections/debops.debops/src"
        _src_dir = os.path.join(dname, "src")
        _crawl_target_path = _src_dir
        _load_path = ""

        print("temporary dir {} created".format(dname))

        _params_before = {
            "_is_ext": True,
            "_target": _target,
            "_target_type": _target_type,
            "_load_output_path": _load_output_path,
            "_load_index_path": _load_index_path,
            "_install_log_path": _install_log_path, 
            "_defs_out_path" : _defs_out_path,
            "_src_dir": _src_dir
        }

        print("before move")
        print(json.dumps(_params_before, indent=2))

        # ansible-galaxy install
        print("installing collections from galaxy")

        install_msg = install_target(_target, _target_type, _src_dir)
        with open(_install_log_path, "w") as f:
            print(install_msg, file=f)
            print(install_msg)

        # ansible-galaxy collection install
        # load src, create load.json
        print("loading collections")
        crawl(_is_ext, _load_output_path, _load_index_path, _crawl_target_path)

        # load index_
        print("decomposing files")
        load_definitions(_is_ext, _load_index_path, _load_path, _defs_out_path)

        # move the files to common dir


        _new_load_index_path = os.path.join(_common_data_dir, "{}-{}-index-ext.json".format(_target_type, _target))
        _new_log_path = os.path.join(_common_data_dir, "{}-{}-install.log".format(_target_type, _target))

        params = {
            "in_path": _common_src_dir,
            "out_path": _common_ext_dir,
        }        

        print("moving index")
        lidx1, lidx2 = move_index(_load_index_path, _new_load_index_path, params)


        print("moving results to common dir")
        out_path = lidx1.get("out_path","")
        generated_load_files = lidx1.get("generated_load_files",[])
        for v in generated_load_files:
            load_file = v["file"]
            target_name = v["name"]
            target_type = v["type"]
            load_file_path = os.path.join(out_path, load_file)
            new_load_file_path = os.path.join(_common_ext_dir, load_file)
            move_load_file(load_file_path, _src_dir, new_load_file_path, _common_src_dir)
            move_definitions(_defs_out_path, _src_dir, _common_def_dir, _common_src_dir, target_name, target_type)

        shutil.move(_install_log_path, _new_log_path)

        _params_after = {
            "_is_ext": True,
            "_target": _target,
            "_target_type": _target_type,
            "_load_output_path": _common_ext_dir,
            "_load_index_path": _new_load_index_path,
            "_install_log_path": _new_log_path, 
            "_defs_out_path" : _common_def_dir,
            "_src_dir": _common_src_dir
        }

        print("after move")
        print(json.dumps(_params_after, indent=2))

    if not os.path.exists(dname):
        print("temporary dir {} cleared".format(dname))
    else:
        print("temporary dir {} remaining somehow...".format(dname))

    # parser = argparse.ArgumentParser(
    #     prog='loader.py',
    #     description='load project/collection(s)/role(s)/playbook and make a load json',
    #     epilog='end',
    #     add_help=True,
    # )

    # parser.add_argument('-t', '--target-path', default="", help='target path')
    # parser.add_argument('-o', '--output-path', default="", help='path to output dir/file')
    # parser.add_argument('-i', '--index-path', default="", help='path to the output index.json')
    # parser.add_argument('--root', action='store_true', help='enable this if the target is the root')
    # parser.add_argument('--ext', action='store_true', help='enable this if the target is the external dependency(s)')

    # args = parser.parse_args()

    # if not args.root and not args.ext:
    #     logging.error("either \"--root\" or \"--ext\" must be specified")
    #     sys.exit(1)

    # if args.root and not args.output_path.endswith(".json"):
    #     logging.error("\"--output-path\" must be a single .json file for \"--root\" mode")
    #     sys.exit(1)

    # is_ext = args.ext
    # output_path = args.output_path
    # index_path = args.index_path
    # crawl_target_path = args.target_path

    # crawl(is_ext, output_path, index_path, crawl_target_path)

    # parser = argparse.ArgumentParser(
    #     prog='parser.py',
    #     description='parse collection/role and its children and output definition json',
    #     epilog='end',
    #     add_help=True,
    # )

    # parser.add_argument('-l', '--load-path', default="", help='load json path/dir')
    # parser.add_argument('-i', '--index-path', default="", help='if specified, load files in this index.json (--load-path will be ignored)')
    # parser.add_argument('--root', action='store_true', help='enable this if the target is the root')
    # parser.add_argument('--ext', action='store_true', help='enable this if the target is the external dependency(s)')
    # parser.add_argument('-o', '--output-dir', default="", help='path to the output dir')

    # args = parser.parse_args()

    # if not args.root and not args.ext:
    #     logging.error("either \"--root\" or \"--ext\" must be specified")
    #     sys.exit(1)
    # is_ext = args.ext

    # if args.load_path == "" and args.index_path == "":
    #     logging.error("either `--load-path` or `--index-path` is required")
    #     sys.exit(1)

    # if args.root and args.load_path == "":
    #     logging.error("\"--load-path\" must be specified for \"--root\" mode")
    #     sys.exit(1)

    # if args.root and not os.path.isfile(args.load_path):
    #     logging.error("\"--load-path\" must be a single .json file for \"--root\" mode")
    #     sys.exit(1)

    # if args.load_path != "" and not os.path.exists(args.load_path):
    #     logging.error("No such file or directory: {}".format(args.load_path))
    #     sys.exit(1)

    # if args.index_path != "" and not os.path.exists(args.index_path):
    #     logging.error("No such file or directory: {}".format(args.index_path))
    #     sys.exit(1)

    # index_path = args.index_path
    # load_path = args.load_path
    # output_path = args.output_dir

    # load_definitions(index_path, load_path, output_path)


