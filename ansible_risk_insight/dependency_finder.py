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
import yaml
import json
import subprocess
import ansible_risk_insight.logger as logger
from .safe_glob import safe_glob

from .models import (
    LoadType,
)


collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"
requirements_yml = "requirements.yml"
galaxy_yml = "galaxy.yml"
GALAXY_yml = "GALAXY.yml"


def find_dependency(type, target, dependency_dir):
    dependencies = {"dependencies": {}, "type": "", "file": ""}
    logger.debug("search dependency")
    if dependency_dir:
        requirements, paths, metadata = load_existing_dependency_dir(dependency_dir)
        dependencies["dependencies"] = requirements
        dependencies["paths"] = paths
        dependencies["metadata"] = metadata
        dependencies["type"] = type
        dependencies["file"] = None
    else:
        if type == LoadType.PROJECT:
            logger.debug("search project dependency")
            requirements, reqyml = find_project_dependency(target)
            dependencies["dependencies"] = requirements
            dependencies["type"] = LoadType.PROJECT
            dependencies["file"] = reqyml
        elif type == LoadType.ROLE:
            logger.debug("search role dependency")
            requirements, mainyml = find_role_dependency(target)
            dependencies["dependencies"] = requirements
            dependencies["type"] = LoadType.ROLE
            dependencies["file"] = mainyml
        elif type == LoadType.COLLECTION:
            logger.debug("search collection dependency")
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
                main_yaml = rf
                with open(rf, "r") as file:
                    try:
                        metadata = yaml.safe_load(file)
                    except Exception as e:
                        logger.debug("failed to load this yaml file to read metadata; {}".format(e.args[0]))

                    if metadata is not None and isinstance(metadata, dict):
                        requirements["roles"] = metadata.get("dependencies", [])
                        requirements["collections"] = metadata.get("collections", [])
    return requirements, main_yaml


def find_collection_dependency(target):
    requirements = {}
    # collection dir installed by ansible-galaxy command
    manifest_json_files = safe_glob(os.path.join(target, "**", collection_manifest_json), recursive=True)
    logger.debug("found meta files {}".format(manifest_json_files))
    manifest_json = ""
    if len(manifest_json_files) > 0:
        for cmf in manifest_json_files:
            if os.path.exists(cmf):
                manifest_json = cmf
                metadata = {}
                with open(cmf, "r") as file:
                    metadata = json.load(file)
                    dependencies = metadata.get("collection_info", {}).get("dependencies", [])
                    requirements["collections"] = format_dependency_info(dependencies)
    else:
        requirements, manifest_json = load_dependency_from_galaxy(target)
    return requirements, manifest_json


def find_project_dependency(target):
    if os.path.exists(target):
        # local dir
        logger.debug("load requirements from dir {}".format(target))
        return load_requirements(target)
    else:
        raise ValueError("Invalid target dir: {}".format(target))


def load_requirements(path):
    requirements = {}
    yaml_path = ""
    # project dir
    requirements_yml_path = os.path.join(path, requirements_yml)
    if os.path.exists(requirements_yml_path):
        yaml_path = requirements_yml_path
        with open(requirements_yml_path, "r") as file:
            try:
                requirements = yaml.safe_load(file)
            except Exception as e:
                logger.debug("failed to load requirements.yml; {}".format(e.args[0]))
    else:
        requirements, yaml_path = load_dependency_from_galaxy(path)
    return requirements, yaml_path


def load_dependency_from_galaxy(path):
    requirements = {}
    yaml_path = ""
    galaxy_yml_files = safe_glob(os.path.join(path, "**", galaxy_yml), recursive=True)
    galaxy_yml_files.extend(safe_glob(os.path.join(path, "**", GALAXY_yml), recursive=True))
    logger.debug("found meta files {}".format(galaxy_yml_files))
    if len(galaxy_yml_files) > 0:
        for g in galaxy_yml_files:
            if os.path.exists(g):
                yaml_path = g
                metadata = {}
                with open(g, "r") as file:
                    metadata = yaml.safe_load(file)
                    dependencies = metadata.get("dependencies", {})
                    requirements["collections"] = format_dependency_info(dependencies)
    return requirements, yaml_path


def load_existing_dependency_dir(dependency_dir):
    # role_meta_files = safe_glob(
    #     [
    #         os.path.join(dependency_dir, "**", role_meta_main_yml),
    #         os.path.join(dependency_dir, "**", role_meta_main_yaml),
    #     ],
    #     recursive=True,
    # )
    collection_meta_files = safe_glob(os.path.join(dependency_dir, "**", collection_manifest_json), recursive=True)
    requirements = {
        "roles": [],
        "collections": [],
    }
    paths = {
        "roles": {},
        "collections": {},
    }
    metadata = {
        "roles": {},
        "collections": {},
    }
    # for r_meta_file in role_meta_files:
    #     role_name = r_meta_file.split("/")[-3]
    #     role_path = "/".join(r_meta_file.split("/")[:-2])
    #     requirements["roles"].append(role_name)
    #     paths["roles"][role_name] = role_path
    for c_meta_file in collection_meta_files:
        if "/tests/" in c_meta_file:
            continue
        parts = c_meta_file.split("/")
        collection_name = f"{parts[-3]}.{parts[-2]}"
        collection_path = "/".join(c_meta_file.split("/")[:-1])
        collection_base_path = "/".join(c_meta_file.split("/")[:-3])
        for dir_name in os.listdir(collection_base_path):
            galaxy_data = None
            if dir_name.startswith(collection_name) and dir_name.endswith(".info"):
                galaxy_yml_path = os.path.join(collection_base_path, dir_name, galaxy_yml)
                try:
                    with open(galaxy_yml_path, "r") as galaxy_yml_file:
                        galaxy_data = yaml.safe_load(galaxy_yml_file)
                except Exception:
                    pass
            if not isinstance(galaxy_data, dict):
                continue
            metadata["collections"][collection_name] = galaxy_data
        requirements["collections"].append(collection_name)
        paths["collections"][collection_name] = collection_path
    return requirements, paths, metadata


def install_github_target(target, output_dir):
    proc = subprocess.run(
        "git clone {} {}".format(target, output_dir),
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    logger.debug("STDOUT: {}".format(install_msg))
    return proc.stdout


def format_dependency_info(dependencies):
    results = []
    for k, v in dependencies.items():
        results.append({"name": k, "version": v})
    return results
