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
import json
import subprocess
import logging
import glob
import re
import shutil

from .models import (
    LoadType,
)
from .dependency_finder import find_dependency


def dependency_dir_preparator(type, target_path, dependency_dir="", root_dir="", cache_enabled=False, cache_dir="", source_repository=""):
    # -- in --#
    # dependencies = {} # {'dependencies': {'collections': []}, 'type': '', 'file': ''}
    # dependency_dir_path = "" # where to unpack tar.gz
    # download_location = "" # path to put tar.gz
    # download_from = "" #  [galaxy/automation hub] -> need to change configuration of ansible cli
    # cache_dir = "" # path to put cache data
    # cache_enabled = False [true/false]

    # --  out --#
    dependency_dirs = []  # {"dir": "", "metadata": {}}
    # metadata : "type", "cache_enabled", "hash", "src"[galaxy/automation hub], version, timestamp, author

    dependencies = find_dependency(type, target_path, dependency_dir)

    download_location = os.path.join(root_dir, "archives", type)
    dependency_dir_path = root_dir

    # check download_location
    if not os.path.exists(download_location):
        os.makedirs(download_location)

    # check cache_dir
    if cache_enabled and not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    # check dependency_dir_path
    if not os.path.exists(dependency_dir_path):
        os.makedirs(dependency_dir_path)

    col_dependencies = dependencies.get("dependencies", {}).get("collections", [])
    role_dependencies = dependencies.get("dependencies", {}).get("roles", [])

    col_dependency_dirs = dependencies.get("paths", {}).get("collections", {})
    role_dependency_dirs = dependencies.get("paths", {}).get("roles", {})

    col_dependency_metadata = dependencies.get("metadata", {}).get("collections", {})
    # role_dependency_metadata = dependencies.get("metadata", {}).get("roles", {})

    # if requirements.yml is provided, download dependencies using it.
    # if dependency_file.endswith("requirements.yml") or dependency_file.endswith("requirements.yaml"):
    #     if cache_enabled:
    #         logging.debug("cache enabled")
    #     else:
    #         logging.debug("all dependencies will be newly downloaded")
    #         if len(col_dependencies) != 0:
    #             download_galaxy_collection_from_reqfile(dependency_file, download_location, source_repository)
    #             install_galaxy_collection_from_targz(download_location, sub_dependency_dir_path)
    #         if len(role_dependencies) != 0:

    #         return dependency_dirs

    for cdep in col_dependencies:
        downloaded_dep = {"dir": "", "metadata": {}}
        downloaded_dep["metadata"]["type"] = LoadType.COLLECTION
        downloaded_dep["metadata"]["name"] = cdep
        downloaded_dep["metadata"]["cache_enabled"] = cache_enabled
        # sub_dependency_dir_path = "{}/{}".format(dependency_dir_path, cdep)
        sub_download_location = "{}/{}".format(download_location, cdep)
        name_parts = cdep.split(".")
        sub_dependency_dir_path = os.path.join(
            dependency_dir_path,
            "collections",
            "src",
            "ansible_collections",
            name_parts[0],
            name_parts[1],
        )
        durl = ""
        version = ""
        if not os.path.exists(sub_dependency_dir_path):
            os.makedirs(sub_dependency_dir_path)
        if cache_enabled:
            logging.debug("cache enabled")
            # search tar.gz file from cache dir ex) ansible.posix -> ansible-posix-1.4.0.tar.gz
            # TODO: handle version
            target = "{}-*.tar.gz".format(cdep.replace(".", "-"))
            dependency_targz_files = glob.glob(os.path.join(cache_dir, "**", target), recursive=True)
            # check cache data
            if len(dependency_targz_files) != 0:
                logging.debug("found cache data {}".format(dependency_targz_files))
                targz_file = dependency_targz_files[0]
                durl, version = load_cache_metadata(targz_file)
            else:
                # if no cache data, download
                logging.debug("cache data not found")
                cache_location = "{}/{}".format(cache_dir, cdep)
                durl, version = download_galaxy_collection(cdep, cache_location, source_repository)
                targz_file = get_targz_collection(cache_location)
                export_cache_metadata(targz_file, cdep, version, durl)

            # install col from tar.gz
            install_galaxy_collection_from_targz(targz_file, sub_dependency_dir_path)
            downloaded_dep["metadata"]["cache_data"] = targz_file
        elif cdep in col_dependency_dirs:
            logging.debug("use the specified dependency dirs")
            sub_dependency_dir_path = col_dependency_dirs[cdep]
            col_galaxy_data = col_dependency_metadata.get(cdep, {})
            if isinstance(col_galaxy_data, dict):
                durl = col_galaxy_data.get("download_url", "")
                version = col_galaxy_data.get("version", "")
        else:
            logging.debug("all dependencies will be newly downloaded")
            # check download_location
            sub_download_location = "{}/{}".format(download_location, cdep)
            if not os.path.exists(sub_download_location):
                os.makedirs(sub_download_location)
            durl, version = download_galaxy_collection(cdep, sub_download_location, source_repository)
            # install dependency in dependency dir
            targz_file = get_targz_collection(sub_download_location)
            install_galaxy_collection_from_targz(targz_file, sub_dependency_dir_path)
        downloaded_dep["metadata"]["source"] = source_repository
        downloaded_dep["metadata"]["download_url"] = durl
        downloaded_dep["metadata"]["version"] = version
        downloaded_dep["dir"] = sub_dependency_dir_path
        dependency_dirs.append(downloaded_dep)

    for rdep in role_dependencies:
        downloaded_dep = {"dir": "", "metadata": {}}
        # metadata
        downloaded_dep["metadata"]["type"] = LoadType.ROLE
        downloaded_dep["metadata"]["name"] = rdep
        # sub_dependency_dir_path = "{}/{}".format(dependency_dir_path, rdep)
        sub_dependency_dir_path = os.path.join(
            dependency_dir_path,
            "roles",
            "src",
            rdep,
        )
        durl = ""
        version = ""
        if not os.path.exists(sub_dependency_dir_path):
            os.makedirs(sub_dependency_dir_path)
        if cache_enabled:
            logging.debug("cache enabled")
            cache_dir_path = os.path.join(
                cache_dir,
                "roles",
                "src",
                rdep,
            )
            if os.path.exists(cache_dir_path) and len(os.listdir(cache_dir_path)) != 0:
                logging.debug("cache data found")
            else:
                logging.debug("cache data not found")
                durl, version = install_galaxy_role(rdep, cache_dir_path)
                # need to put metadata when cache
            durl, version = get_cache_role_data(sub_dependency_dir_path, cache_dir_path, rdep)
        elif rdep in role_dependency_dirs:
            logging.debug("use the specified dependency dirs")
            sub_dependency_dir_path = role_dependency_dirs[rdep]
        else:
            logging.debug("all dependencies will be newly downloaded")
            # check download_location
            durl, version = install_galaxy_role(rdep, sub_dependency_dir_path)
        downloaded_dep["metadata"]["source"] = source_repository
        downloaded_dep["metadata"]["download_url"] = durl
        downloaded_dep["metadata"]["version"] = version
        downloaded_dep["dir"] = sub_dependency_dir_path
        dependency_dirs.append(downloaded_dep)
    return dependency_dirs


def download_galaxy_collection(target, output_dir, source_repository=""):
    server_option = ""
    if source_repository != "":
        server_option = "--server {}".format(source_repository)
    proc = subprocess.run(
        "ansible-galaxy collection download {} {} -p {}".format(target, server_option, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    logging.debug("STDOUT: {}".format(install_msg))
    durl, version = get_collection_metadata_from_log(install_msg)
    return durl, version
    # return proc.stdout


def download_galaxy_collection_from_reqfile(requirementes, output_dir, source_repository=""):
    server_option = ""
    if source_repository != "":
        server_option = "--server {}".format(source_repository)
    proc = subprocess.run(
        "ansible-galaxy collection download -r {} {} -p {}".format(requirementes, server_option, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    logging.debug("STDOUT: {}".format(install_msg))
    # return proc.stdout


def get_targz_collection(download_location):
    tarfile_list = []
    for file in os.listdir(download_location):
        if file.endswith(".tar.gz"):
            tarfile = os.path.join(download_location, file)
            tarfile_list.append(tarfile)
    logging.debug("found tar.gz files {}".format(",".join(tarfile_list)))
    return tarfile_list[0]


def install_galaxy_collection_from_targz(tarfile, output_dir):
    logging.debug("install collection from ", tarfile)
    proc = subprocess.run(
        "ansible-galaxy collection install {} -p {}".format(tarfile, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    logging.debug("STDOUT: {}".format(install_msg))
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
    logging.debug("STDOUT: {}".format(install_msg))
    # url, version = get_role_metadata_from_log(install_msg)
    url = ""
    version = ""
    return url, version


def get_cache_role_data(sub_dependency_dir_path, cache_dir_path, rdep):
    copy_to = "{}/{}".format(sub_dependency_dir_path, rdep)
    if len(os.listdir(copy_to)) != 0:
        logging.debug("dir {} already exists. clear the dir.".format(copy_to))
        shutil.rmtree(copy_to)
    logging.debug("copy cache data {} to {}".format(cache_dir_path, copy_to))
    shutil.copytree(cache_dir_path, copy_to)
    url = ""
    version = ""
    return url, version


def install_galaxy_role_from_reqfile(file, output_dir):
    proc = subprocess.run(
        "ansible-galaxy role install -r {} -p {}".format(file, output_dir),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    logging.debug("STDOUT: {}".format(install_msg))


def get_collection_metadata_from_log(log_message):
    # -- log message
    # Downloading collection 'community.rabbitmq:1.2.3' to
    # Downloading https://galaxy.ansible.com/download/ansible-posix-1.4.0.tar.gz to ...
    download_url_pattern = r"Downloading (.*) to"
    url = ""
    version = ""
    m = re.findall(download_url_pattern, log_message)
    logging.debug(m)
    url = m[1]
    version = m[0].replace("'", "").split(":")[1]
    logging.debug(version)
    return url, version


def export_cache_metadata(targz_file, dep, version, durl):
    metafile = targz_file.replace(".tar.gz", "-meta.json")
    name_parts = dep.split(".")
    metadata = {"name": name_parts[1], "namespace": name_parts[0], "download_url": durl, "version": version, "download_time": ""}
    with open(metafile, "w") as f:
        json.dump(metadata, f)


def load_cache_metadata(targz_file):
    metafile = targz_file.replace(".tar.gz", "-meta.json")
    if not os.path.exists(metafile):
        logging.debug("metadata for {} not found".format(targz_file))
        return "", ""
    with open(metafile) as f:
        data = json.load(f)
    return data.get("download_url", ""), data.get("version", "")


def get_role_metadata_from_log(log_message):
    # -- log message
    # - downloading role from https://github.com/geerlingguy/ansible-role-gitlab/archive/3.2.0.tar.gz
    # - geerlingguy.gitlab (3.2.0) was installed successfully
    download_url_pattern = r"- downloading role from (.*) -"
    version_pattern = r"- (.*) was installed successfully"
    url = ""
    version = ""
    m = re.findall(download_url_pattern, log_message)
    logging.debug(m)
    url = m[0]
    m2 = re.findall(version_pattern, log_message)
    version = m2[0].split("(")[1].split(")")[0]
    logging.debug(version)
    return url, version


def existing_dependency_dir_loader(dependency_type, dependency_dir_path):
    search_dirs = []
    if dependency_type == LoadType.COLLECTION:
        base_dir = dependency_dir_path
        if os.path.exists(os.path.join(dependency_dir_path, "ansible_collections")):
            base_dir = os.path.join(dependency_dir_path, "ansible_collections")
        namespaces = [ns for ns in os.listdir(base_dir) if not ns.endswith(".info")]
        for ns in namespaces:
            colls = [{"name": f"{ns}.{name}", "path": os.path.join(base_dir, ns, name)} for name in os.listdir(os.path.join(base_dir, ns))]
            search_dirs.extend(colls)

    dependency_dirs = []
    for dep_info in search_dirs:
        downloaded_dep = {"dir": "", "metadata": {}}
        downloaded_dep["dir"] = dep_info["path"]
        # meta data
        downloaded_dep["metadata"]["type"] = LoadType.COLLECTION
        downloaded_dep["metadata"]["name"] = dep_info["name"]
        dependency_dirs.append(downloaded_dep)
    return dependency_dirs


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument("dependencies", help="Target dir")
    parser.add_argument("download_location")
    parser.add_argument("dependency_dir_path")
    parser.add_argument("--cache", action="store_true")
    parser.add_argument("cache_dir")
    # parser.add_argument("name", help="Content name")

    args = parser.parse_args()
    dependencies = json.loads(args.dependencies)
    result = dependency_dir_preparator(dependencies, args.download_location, args.dependency_dir_path, args.cache, args.cache_dir)
    logging.debug(json.dumps(result, indent=2))
