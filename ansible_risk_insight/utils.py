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
import subprocess
import requests
import hashlib
import yaml
import logging

from .findings import Findings


def install_galaxy_target(target, target_type, output_dir, source_repository="", target_version=""):
    server_option = ""
    if source_repository != "" and source_repository is not None:
        server_option = "--server {}".format(source_repository)
    target_name = target
    if target_version != "":
        target_name = f"{target}:{target_version}"
    logging.debug("exec ansible-galaxy cmd: ansible-galaxy {} install {} {} -p {}".format(target_type, target_name, server_option, output_dir))
    proc = subprocess.run(
        "ansible-galaxy {} install {} {} -p {}".format(target_type, target_name, server_option, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def install_github_target(target, output_dir):
    proc = subprocess.run(
        "git clone {} {}".format(target, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def get_download_metadata(typ: str, install_msg: str):
    download_url = ""
    version = ""
    if typ == "collection":
        for line in install_msg.splitlines():
            if line.startswith("Downloading "):
                download_url = line.split(" ")[1]
                version = download_url.split("-")[-1].replace(".tar.gz", "")
                break
    elif typ == "role":
        for line in install_msg.splitlines():
            if line.startswith("- downloading role from "):
                download_url = line.split(" ")[-1]
                version = download_url.split("/")[-1].replace(".tar.gz", "")
                break
    hash = ""
    if download_url != "":
        hash = get_hash_of_url(download_url)
    return download_url, version, hash


def get_installed_metadata(type, name, path, dep_dir=None):
    if dep_dir:
        dep_dir_alt = os.path.join(dep_dir, "ansible_collections")
        if os.path.exists(dep_dir_alt):
            dep_dir = dep_dir_alt
        parts = name.split(".")
        if len(parts) == 1:
            parts.append("dummy")
        dep_dir_target_path = os.path.join(dep_dir, parts[0], parts[1])
        download_url, version = get_installed_metadata(type, name, dep_dir_target_path)
        if download_url or version:
            return download_url, version
    download_url = ""
    version = ""
    galaxy_yml = "GALAXY.yml"
    galaxy_data = None
    if type == "collection":
        base_dir = "/".join(path.split("/")[:-2])
        dirs = os.listdir(base_dir)
        for dir_name in dirs:
            tmp_galaxy_data = None
            if dir_name.startswith(name) and dir_name.endswith(".info"):
                galaxy_yml_path = os.path.join(base_dir, dir_name, galaxy_yml)
                try:
                    with open(galaxy_yml_path, "r") as galaxy_yml_file:
                        tmp_galaxy_data = yaml.safe_load(galaxy_yml_file)
                except Exception:
                    pass
            if isinstance(tmp_galaxy_data, dict):
                galaxy_data = tmp_galaxy_data
    if galaxy_data is not None:
        download_url = galaxy_data.get("download_url", "")
        version = galaxy_data.get("version", "")
    return download_url, version


def escape_url(url: str):
    base_url = url.split("?")[0]
    replaced = base_url.replace("://", "__").replace("/", "_")
    return replaced


def get_hash_of_url(url: str):
    response = requests.get(url)
    hash = hashlib.sha256(response.content).hexdigest()
    return hash


def split_name_and_version(target_name):
    name = target_name
    version = ""
    if ":" in target_name:
        parts = target_name.split(":")
        name = parts[0]
        version = parts[1]
    return name, version


def version_to_num(ver: str):
    if ver == "unknown":
        return 0
    # version string can be 1.2.3-abcdxyz
    ver_num_part = ver.split("-")[0]
    parts = ver_num_part.split(".")
    num = 0
    if len(parts) >= 1:
        if parts[0].isnumeric():
            num += float(parts[0])
    if len(parts) >= 2:
        if parts[1].isnumeric():
            num += float(parts[1]) * (0.001**1)
    if len(parts) >= 3:
        if parts[2].isnumeric():
            num += float(parts[2]) * (0.001**2)
    return num


def is_url(txt: str):
    return "://" in txt


def show_findings(findings: Findings):
    print("[DEBUG] findings:", findings)
