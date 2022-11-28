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

import argparse
import os
import yaml
import json
import subprocess
import logging
from .safe_glob import safe_glob

from .models import (
    LoadType,
)


collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"
requirements_yml = "requirements.yml"


def find_dependency(type, target):
    dependencies = {"dependencies": "", "type": "", "file": ""}
    print("search dependency")
    if type == LoadType.PROJECT:
        print("search project dependency")
        requirements, reqyml = find_project_dependency(target)
        dependencies["dependencies"] = requirements
        dependencies["type"] = LoadType.PROJECT
        dependencies["file"] = reqyml
    elif type == LoadType.ROLE:
        print("search role dependency")
        requirements, mainyml = find_role_dependency(target)
        dependencies["dependencies"] = requirements
        dependencies["type"] = LoadType.ROLE
        dependencies["file"] = mainyml
    elif type == LoadType.COLLECTION:
        print("search collection dependency")
        requirements, manifestjson = find_collection_dependency(target)
        dependencies["dependencies"] = requirements
        dependencies["type"] = LoadType.COLLECTION
        dependencies["file"] = manifestjson
    return dependencies


def find_role_dependency(target):
    requirements = {}
    if not os.path.exists(target):
        raise ValueError("Invalid target dir: {}".format(target))
    role_meta_files = safe_glob(
        [
            os.path.join(target, "**", role_meta_main_yml),
            os.path.join(target, "**", role_meta_main_yaml),
        ],
        recursive=True,
    )
    main_yaml = ""
    if len(role_meta_files) > 0:
        for rf in role_meta_files:
            if os.path.exists(rf):
                with open(rf, "r") as file:
                    try:
                        metadata = yaml.safe_load(file)
                    except Exception as e:
                        logging.error("failed to load this yaml file to read metadata; {}".format(e.args[0]))

                    if metadata is not None and isinstance(metadata, dict):
                        requirements["roles"] = metadata.get("dependencies", [])
                        requirements["collections"] = metadata.get("collections", [])
                if main_yaml == "":
                    with open(rf, "r") as file:
                        main_yaml = file.read()
    return requirements, main_yaml


def find_collection_dependency(target):
    requirements = {}
    collection_meta_files = safe_glob(os.path.join(target, "**", collection_manifest_json), recursive=True)
    print("found meta files {}".format(collection_meta_files))
    manifest_json = ""
    if len(collection_meta_files) > 0:
        for cmf in collection_meta_files:
            if os.path.exists(cmf):
                metadata = {}
                with open(cmf, "r") as file:
                    metadata = json.load(file)
                    dependencies = metadata.get("collection_info", {}).get("dependencies", [])
                    requirements["collections"] = list(dependencies.keys())  # need to handle version info
                if manifest_json == "":
                    with open(cmf, "r") as file:
                        manifest_json = file.read()
    return requirements, manifest_json


def find_project_dependency(target):
    # url or dir
    # if validators.url(target):
    #     print("cloning {} from github".format(target))

    #     install_msg = install_github_target(target, tmp_src_dir)
    # elif os.path.exists(target):
    if os.path.exists(target):
        # requirements.yml or local dir
        print("load requirements from dir {}".format(target))
        return load_requirements(target)
    else:
        raise ValueError("Invalid target dir: {}".format(target))


def load_requirements(path):
    requirements = {}
    requirements_yml_path = os.path.join(path, requirements_yml)
    if os.path.exists(requirements_yml_path):
        with open(requirements_yml_path, "r") as file:
            try:
                requirements = yaml.safe_load(file)
            except Exception as e:
                logging.error("failed to load requirements.yml; {}".format(e.args[0]))
    return requirements, requirements_yml_path


def install_github_target(target, output_dir):
    proc = subprocess.run(
        "git clone {} {}".format(target, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    print("STDOUT: {}".format(install_msg))
    return proc.stdout


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument("target_dir", help="Target dir")
    parser.add_argument("type", help="Content type", choices={"project", "role", "collection"})
    # parser.add_argument("name", help="Content name")

    args = parser.parse_args()
    result = find_dependency(args.type, args.target_dir)
    print(result)
