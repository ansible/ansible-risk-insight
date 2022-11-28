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
import validators
import subprocess
import logging
from shutil import unpack_archive, make_archive
from safe_glob import safe_glob

# from .models import (
#     LoadType,
# )

class LoadType:
    COLLECTION = "collection"
    ROLE = "role"
    PROJECT = "project"


def dependency_downloader():
    
    return

def dependency_dir_preparator(dependencies, download_location, dependency_dir_path, cache_enabled, cache_dir):
    ### in ###
    # dependencies = {} # {'dependencies': {'collections': []}, 'type': '', 'file': ''}
    # dependency_dir_path = "" # where to unpack tar.gz
    # download_location = "" # path to put tar.gz
    # download_from = "" #  [galaxy/automation hub] -> need to change configuration of ansible cli
    # cache_dir = "" # path to put cached data
    # cache_enabled = False [true/false]

    ###  out ###
    dependency_dirs = [] # {"dir": "", "metadata": {}}
    # metadata : "type", "cache_enabled", "hash", "src"[galaxy/automation hub], version, timestamp, author

    # check download_location
    if not os.path.exists(download_location):
        os.makedirs(download_location)

    # check cache_dir
    if cache_enabled and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    
    # check dependency_dir_path
    if not os.path.exists(dependency_dir_path):
        os.makedirs(dependency_dir_path)

    dependency_file = dependencies.get("file", "")
    col_dependencies = dependencies.get("dependencies", {}).get("collections", [])
    role_dependencies = dependencies.get("dependencies", {}).get("roles", [])
    # if requirements.yml is provided, download dependencies using it.
    # if dependency_file.endswith("requirements.yml") or dependency_file.endswith("requirements.yaml"):
    #     if cache_enabled:
    #         print("cache enabled")
    #     else:
    #         print("all dependencies will be newly downloaded")
    #         if len(col_dependencies) != 0:
    #             download_galaxy_collection_from_reqfile(dependency_file, download_location)
    #             install_galaxy_collection_from_targz(download_location, sub_dependency_dir_path)
    #         if len(role_dependencies) != 0:
                
    #         return dependency_dirs

    for cdep in col_dependencies:
        downloaded_dep = {"dir": "", "metadata": {}}
        sub_download_location = "{}/{}".format(download_location, cdep)
        sub_dependency_dir_path = "{}/{}".format(dependency_dir_path, cdep)
        if cache_enabled:
            print("cache enabled")
        else:
            print("all dependencies will be newly downloaded")
            # check download_location
            if not os.path.exists(sub_download_location):
                os.makedirs(sub_download_location) 
            download_galaxy_collection(cdep, sub_download_location)
            # install dependency in dependency dir
            if not os.path.exists(sub_dependency_dir_path):
                os.makedirs(sub_dependency_dir_path) 
            install_galaxy_collection_from_targz(sub_download_location, sub_dependency_dir_path)
        downloaded_dep["dir"] = sub_dependency_dir_path
        # meta data
        downloaded_dep["metadata"]["type"] = LoadType.COLLECTION
        dependency_dirs.append(downloaded_dep)
    
    
    for rdep in role_dependencies:
        downloaded_dep = {"dir": "", "metadata": {}}
        sub_download_location = "{}/{}".format(download_location, rdep)
        sub_dependency_dir_path = "{}/{}".format(dependency_dir_path, rdep)
        if cache_enabled:
            print("cache enabled")
        else:
            print("all dependencies will be newly downloaded")
            # check download_location
            if not os.path.exists(sub_download_location):
                os.makedirs(sub_download_location) 
            install_galaxy_role(rdep, sub_download_location)
            downloaded_dep["dir"] = sub_dependency_dir_path
            # meta data
            downloaded_dep["metadata"]["type"] = LoadType.ROLE
            dependency_dirs.append(downloaded_dep)
    return dependency_dirs     

def download_galaxy_collection(target, output_dir):
    proc = subprocess.run(
        "ansible-galaxy collection download {} -p {}".format(target, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    print("STDOUT: {}".format(install_msg))
    # return proc.stdout

def download_galaxy_collection_from_reqfile(requirementes, output_dir):
    proc = subprocess.run(
        "ansible-galaxy collection download -r {} -p {}".format(requirementes, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    print("STDOUT: {}".format(install_msg))
    # return proc.stdout

def install_galaxy_collection_from_targz(download_location, output_dir):
    # requirement = "{}/requirements.yml".format(download_location)
    for file in os.listdir(download_location):
        if file.endswith(".tar.gz"):
            tarfile = os.path.join(download_location, file)
            print("install collection from ", tarfile)
            proc = subprocess.run(
                "ansible-galaxy collection install {} -p {}".format(tarfile, output_dir),
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            install_msg = proc.stdout
            print("STDOUT: {}".format(install_msg))
            # return proc.stdout

def install_galaxy_role(target, output_dir):
    proc = subprocess.run(
        "ansible-galaxy role install {} -p {}".format(target, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    print("STDOUT: {}".format(install_msg)) 

def install_galaxy_role_from_reqfile(file, output_dir):
    proc = subprocess.run(
        "ansible-galaxy role install -r {} -p {}".format(file, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    print("STDOUT: {}".format(install_msg)) 


def unzip_downloaded_role(compressed_dir, output_dir):
    # unpack
    unpack_archive(filename=compressed_dir, extract_dir=output_dir, format="gztar")            



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument("dependencies", help="Target dir")
    parser.add_argument("download_location")
    parser.add_argument("dependency_dir_path")
    # parser.add_argument("name", help="Content name")

    args = parser.parse_args()
    dependencies = json.loads(args.dependencies)
    # dependencies = {'dependencies': {'collections': ['ansible.posix', 'community.crypto', 'community.general', 'community.libvirt', 'community.mysql', 'community.postgresql', 'community.rabbitmq']}, 'type': 'project', 'file': '../../ansible-dev/debops/requirements.yml'}
    result = dependency_dir_preparator(dependencies, args.download_location, args.dependency_dir_path, False, "/tmp/ari-cache")
    print(result)
