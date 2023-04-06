# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2022 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pathlib
import json
import pygit2
import pkg_resources
from .models import LoadType

collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"


# remove a dir which is a sub directory of another dir in the list
def remove_subdirectories(dir_list):
    sorted_dir_list = sorted(dir_list)
    new_dir_list = []
    for i, dir in enumerate(sorted_dir_list):
        if i >= 1 and dir.startswith(sorted_dir_list[i - 1]):
            continue
        new_dir_list.append(dir)
    return new_dir_list


def trim_suffix(txt, suffix_patterns=[]):
    if isinstance(suffix_patterns, str):
        suffix_patterns = [suffix_patterns]
    if not isinstance(suffix_patterns, list):
        return txt
    for suffix in suffix_patterns:
        if txt.endswith(suffix):
            return txt[: -len(suffix)]
    return txt


def get_loader_version():
    version = ""
    # try to get version from the installed executable
    try:
        version = pkg_resources.require("ansible-risk-insight")[0].version
    except Exception:
        pass
    if version != "":
        return version
    # try to get version from commit ID in source code repository
    try:
        script_dir = pathlib.Path(__file__).parent.resolve()
        repo = pygit2.Repository(script_dir)
        version = repo.head.target
    except Exception:
        pass
    return version


def get_target_name(target_type, target_path):
    target_name = ""
    if target_type == LoadType.PROJECT:
        project_name = os.path.normpath(target_path).split("/")[-1]
        target_name = project_name
    elif target_type == LoadType.COLLECTION:
        meta_file = os.path.join(target_path, collection_manifest_json)
        metadata = {}
        with open(meta_file, "r") as file:
            metadata = json.load(file)
        collection_namespace = metadata.get("collection_info", {}).get("namespace", "")
        collection_name = metadata.get("collection_info", {}).get("name", "")
        target_name = "{}.{}".format(collection_namespace, collection_name)
    elif target_type == LoadType.ROLE:
        # any better approach?
        target_name = target_path.split("/")[-1]
    elif target_type == LoadType.PLAYBOOK:
        target_name = filepath_to_target_name(target_path)
    return target_name


def filepath_to_target_name(filepath):
    return filepath.translate(str.maketrans({" ": "___", "/": "---", ".": "_dot_"}))


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         prog="loader.py",
#         description=(
#             "load project/collection(s)/role(s)/playbook and make a load json"
#         ),
#         epilog="end",
#         add_help=True,
#     )

#     parser.add_argument("-t", "--target-path", default="", help="target path")
#     parser.add_argument(
#         "-o", "--output-path", default="", help="path to output dir/file"
#     )
#     parser.add_argument(
#         "-i", "--index-path", default="", help="path to the output index.json"
#     )
#     parser.add_argument(
#         "--root",
#         action="store_true",
#         help="enable this if the target is the root",
#     )
#     parser.add_argument(
#         "--ext",
#         action="store_true",
#         help="enable this if the target is the external dependency(s)",
#     )

#     args = parser.parse_args()

#     if not args.root and not args.ext:
#         logger.error('either "--root" or "--ext" must be specified')
#         sys.exit(1)

#     if args.root and not args.output_path.endswith(".json"):
#         logger.error(
#             '"--output-path" must be a single .json file for "--root" mode'
#         )
#         sys.exit(1)

#     is_ext = args.ext

#     target_type, target_path_list = detect_target_type(
#         args.target_path, is_ext
#     )
#     logger.info(
#         'the detected target type: "{}", found targets: {}'.format(
#             target_type, len(target_path_list)
#         )
#     )
#     if target_type not in supported_target_types:
#         logger.error("this target type is not supported")
#         sys.exit(1)

#     profiles = [(target_path) for target_path in target_path_list]

#     num = len(profiles)
#     if num == 0:
#         logger.info("no target dirs found. exitting.")
#         sys.exit()
#     else:
#         logger.info("start loading {} {}(s)".format(num, target_type))
#     output_path = args.output_path
#     loader_version = get_loader_version()

#     def load_single(single_input):
#         i = single_input[0]
#         num = single_input[1]
#         target_path = os.path.normpath(single_input[2])
#         output_path = single_input[3]
#         is_ext = single_input[4]
#         loader_version = single_input[5]
#         load_json_path = output_path
#         target_name = get_target_name(target_type, target_path)
#         if is_ext:
#             load_json_path = create_load_json_path(
#                 target_type, target_name, output_path
#             )
#         if os.path.exists(load_json_path):
#             d = json.load(open(load_json_path, "r"))
#             timestamp = d.get("timestamp", "")
#             if timestamp != "":
#                 loaded_time = datetime.datetime.fromisoformat(timestamp)
#                 now = datetime.datetime.utcnow()
#                 # if the load data was updated within last 10 minutes, skip it
#                 if (now - loaded_time).total_seconds() < 60 * 10:
#                     print(
#                         "[{}/{}] SKIP: {} {}       ".format(
#                             i + 1, num, target_type, target_name
#                         )
#                     )
#                     return
#         print(
#             "[{}/{}] {} {}       ".format(
#                 i + 1, num, target_type, target_name
#             )
#         )

#         if not os.path.exists(target_path):
#             raise ValueError(
#                 "No such file or directory: {}".format(target_path)
#             )
#         load_json_dir = os.path.dirname(load_json_path)
#         if not os.path.exists(load_json_dir):
#             os.makedirs(load_json_dir, exist_ok=True)
#         ld = Load(
#             target_name=target_name,
#             target_type=target_type,
#             path=target_path,
#             loader_version=loader_version,
#         )
#         ld.run(output_path=load_json_path)

#     parallel_input_list = [
#         (i, num, target_path, output_path, is_ext, loader_version)
#         for i, (target_path) in enumerate(profiles)
#     ]
#     _ = joblib.Parallel(n_jobs=-1)(
#         joblib.delayed(load_single)(single_input)
#         for single_input in parallel_input_list
#     )

#     if args.index_path != "":
#         index_data = {
#             "in_path": args.target_path,
#             "out_path": args.output_path,
#             "mode": "ext" if is_ext else "root",
#             "target_type": target_type,
#             "generated_load_files": [],
#         }

#         generated_load_files = []
#         if is_ext:

#             for target_path in profiles:
#                 target_name = get_target_name(target_type, target_path)
#                 load_json_path = create_load_json_path(
#                     target_type, target_name, args.output_path
#                 )
#                 lf = load_json_path.replace(args.output_path, "")
#                 if lf.startswith("/"):
#                     lf = lf[1:]
#                 generated_load_files.append(
#                     {
#                         "file": lf,
#                         "name": target_name,
#                         "type": target_type,
#                     }
#                 )
#         else:
#             generated_load_files = [
#                 {"file": args.output_path, "name": "", "type": ""}
#             ]
#         index_data["generated_load_files"] = generated_load_files

#         with open(args.index_path, "w") as file:
#             json.dump(index_data, file)
