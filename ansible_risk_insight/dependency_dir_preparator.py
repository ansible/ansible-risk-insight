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
import json
import yaml
import subprocess
import tempfile
import glob
import re
import sys
import datetime
import tarfile
from copy import deepcopy
from dataclasses import dataclass, field, asdict

import ansible_risk_insight.logger as logger
from .models import (
    LoadType,
)
from .dependency_finder import find_dependency
from .utils import (
    escape_url,
    install_galaxy_target,
    install_github_target,
    get_installed_metadata,
    get_hash_of_url,
    is_url,
    is_local_path,
)
from .loader import (
    get_target_name,
    remove_subdirectories,
    trim_suffix,
)
from .safe_glob import safe_glob

collection_manifest_json = "MANIFEST.json"
collection_files_json = "FILES.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"
requirements_yml = "requirements.yml"

supported_target_types = [
    LoadType.PROJECT,
    LoadType.COLLECTION,
    LoadType.ROLE,
    LoadType.PLAYBOOK,
]

download_metadata_file = "download_meta.json"


@dataclass
class DownloadMetadata(object):
    name: str = ""
    type: str = ""
    version: str = ""
    author: str = ""
    download_url: str = ""
    download_src_path: str = ""  # path to put tar.gz
    hash: str = ""
    metafile_path: str = ""  # path to manifest.json/meta.yml
    files_json_path: str = ""
    download_timestamp: str = ""
    cache_enabled: bool = False
    cache_dir: str = ""  # path to put cache data
    source_repository: str = ""
    requirements_file: str = ""


@dataclass
class Dependency(object):
    dir: str = ""
    name: str = ""
    metadata: DownloadMetadata = field(default_factory=DownloadMetadata)


@dataclass
class DependencyDirPreparator(object):
    root_dir: str = ""
    source_repository: str = ""
    target_type: str = ""
    target_name: str = ""
    target_version: str = ""
    target_path: str = ""
    target_dependency_dir: str = ""
    target_path_mappings: dict = field(default_factory=dict)
    metadata: DownloadMetadata = field(default_factory=DownloadMetadata)
    download_location: str = ""
    dependency_dir_path: str = ""
    silent: bool = False
    do_save: bool = False
    tmp_install_dir: tempfile.TemporaryDirectory = None
    periodical_cleanup: bool = False
    cleanup_queue: list = field(default_factory=list)
    cleanup_threshold: int = 200

    # -- out --
    dependency_dirs: list = field(default_factory=list)

    def prepare_dir(self, root_install=True, is_src_installed=False, cache_enabled=False, cache_dir=""):
        logger.debug("setup base dirs")
        self.setup_dirs(cache_enabled, cache_dir)
        logger.debug("prepare target dir")
        self.prepare_root_dir(root_install, is_src_installed, cache_enabled, cache_dir)

        prepare_dependency = False
        # if a project target is a local path, check dependency
        if self.target_type in [LoadType.PROJECT, LoadType.PLAYBOOK, LoadType.TASKFILE] and not is_url(self.target_name):
            prepare_dependency = True
        # if a collection/role is a local path, check dependency
        if self.target_type in [LoadType.COLLECTION, LoadType.ROLE] and is_local_path(self.target_name):
            prepare_dependency = True
        if prepare_dependency:
            logger.debug("search dependencies")
            dependencies = find_dependency(self.target_type, self.target_path, self.target_dependency_dir)
            logger.debug("prepare dir for dependencies")
            self.prepare_dependency_dir(dependencies, cache_enabled, cache_dir)
        return self.dependency_dirs

    def setup_dirs(self, cache_enabled=False, cache_dir=""):
        self.download_location = os.path.join(self.root_dir, "archives")
        self.dependency_dir_path = self.root_dir
        # check download_location
        if not os.path.exists(self.download_location):
            os.makedirs(self.download_location)
        # check cache_dir
        if cache_enabled and not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
        # check dependency_dir_path
        if not os.path.exists(self.dependency_dir_path):
            os.makedirs(self.dependency_dir_path)
        return

    def prepare_root_dir(self, root_install=True, is_src_installed=False, cache_enabled=False, cache_dir=""):
        # install root
        if is_src_installed:
            pass
        else:
            # if a project target is a local path, then skip install
            if self.target_type in [LoadType.PROJECT, LoadType.PLAYBOOK, LoadType.TASKFILE] and not is_url(self.target_name):
                root_install = False

            # if a collection/role is a local path, then skip install (require MANIFEST.json or meta/main.yml to get the actual name)
            if self.target_type in [LoadType.COLLECTION, LoadType.ROLE] and is_local_path(self.target_name):
                root_install = False

            cache_found = False
            if cache_enabled:
                is_exist, targz_file = self.is_download_file_exist(self.target_type, self.target_name, cache_dir)
                # check cache data
                if is_exist:
                    metadata_file = os.path.join(targz_file.rsplit("/", 1)[0], download_metadata_file)
                    md = self.find_target_metadata(self.target_type, metadata_file, self.target_name)
                    if md and os.path.exists(md.source_repository):
                        self.metadata = md
                        cache_found = True
            if cache_found:
                pass
            else:
                if root_install:
                    self.src_install()
                    if not self.silent:
                        logger.debug("install() done")
                else:
                    download_url = ""
                    version = ""
                    hash = ""
                    download_url, version = get_installed_metadata(self.target_type, self.target_name, self.target_path, self.target_dependency_dir)
                    if download_url != "":
                        hash = get_hash_of_url(download_url)
                    self.metadata.download_url = download_url
                    self.metadata.version = version
                    self.metadata.hash = hash
        return

    def prepare_dependency_dir(self, dependencies, cache_enabled=False, cache_dir=""):
        col_dependencies = dependencies.get("dependencies", {}).get("collections", [])
        role_dependencies = dependencies.get("dependencies", {}).get("roles", [])

        col_dependency_dirs = dependencies.get("paths", {}).get("collections", {})
        role_dependency_dirs = dependencies.get("paths", {}).get("roles", {})

        col_dependency_metadata = dependencies.get("metadata", {}).get("collections", {})
        # role_dependency_metadata = dependencies.get("metadata", {}).get("roles", {})

        if col_dependencies:
            for cdep in col_dependencies:
                col_name = cdep
                col_version = ""
                if type(cdep) is dict:
                    col_name = cdep.get("name", "")
                    col_version = cdep.get("version", "")
                    if col_name == "":
                        col_name = cdep.get("source", "")

                logger.debug("prepare dir for {}:{}".format(col_name, col_version))
                downloaded_dep = Dependency(
                    name=col_name,
                )
                downloaded_dep.metadata.type = LoadType.COLLECTION
                downloaded_dep.metadata.name = col_name
                downloaded_dep.metadata.cache_enabled = cache_enabled
                sub_dependency_dir_path = os.path.join(
                    self.dependency_dir_path,
                    "collections",
                    "src",
                )

                if not os.path.exists(sub_dependency_dir_path):
                    os.makedirs(sub_dependency_dir_path)
                if cache_enabled:
                    logger.debug("cache enabled")
                    # TODO: handle version
                    is_exist, targz_file = self.is_download_file_exist(LoadType.COLLECTION, col_name, cache_dir)
                    # check cache data
                    if is_exist:
                        logger.debug("found cache data {}".format(targz_file))
                        metadata_file = os.path.join(targz_file.rsplit("/", 1)[0], download_metadata_file)
                        md = self.find_target_metadata(LoadType.COLLECTION, metadata_file, col_name)
                        downloaded_dep.metadata = md
                    else:
                        # if no cache data, download
                        logger.debug("cache data not found")
                        cache_location = os.path.join(cache_dir, "collection", col_name)
                        install_msg = self.download_galaxy_collection(col_name, cache_location, col_version, self.source_repository)
                        metadata = self.extract_collections_metadata(install_msg, cache_location)
                        metadata_file = self.export_data(metadata, cache_location, download_metadata_file)
                        md = self.find_target_metadata(LoadType.COLLECTION, metadata_file, col_name)
                        downloaded_dep.metadata = md
                        if md:
                            targz_file = md.download_src_path
                    # install collection from tar.gz
                    self.install_galaxy_collection_from_targz(targz_file, sub_dependency_dir_path)
                    downloaded_dep.metadata.cache_dir = targz_file
                    parts = col_name.split(".")
                    full_path = os.path.join(sub_dependency_dir_path, "ansible_collections", parts[0], parts[1])
                    downloaded_dep.dir = full_path.replace(f"{self.root_dir}/", "")
                elif col_name in col_dependency_dirs:
                    logger.debug("use the specified dependency dirs")
                    sub_dependency_dir_path = col_dependency_dirs[col_name]
                    col_galaxy_data = col_dependency_metadata.get(col_name, {})
                    if isinstance(col_galaxy_data, dict):
                        download_url = col_galaxy_data.get("download_url", "")
                        hash = ""
                        if download_url:
                            hash = get_hash_of_url(download_url)
                        version = col_galaxy_data.get("version", "")
                        downloaded_dep.metadata.source_repository = self.source_repository
                        downloaded_dep.metadata.download_url = download_url
                        downloaded_dep.metadata.hash = hash
                        downloaded_dep.metadata.version = version
                        downloaded_dep.dir = sub_dependency_dir_path
                else:
                    logger.debug("download dependency {}".format(col_name))
                    is_exist, targz = self.is_download_file_exist(
                        LoadType.COLLECTION, col_name, os.path.join(self.download_location, "collection", col_name)
                    )
                    if is_exist:
                        metadata_file = os.path.join(self.download_location, "collection", col_name, download_metadata_file)
                        self.install_galaxy_collection_from_targz(targz, sub_dependency_dir_path)
                        md = self.find_target_metadata(LoadType.COLLECTION, metadata_file, col_name)
                    else:
                        # check download_location
                        sub_download_location = os.path.join(self.download_location, "collection", col_name)
                        if not os.path.exists(sub_download_location):
                            os.makedirs(sub_download_location)
                        install_msg = self.download_galaxy_collection(col_name, sub_download_location, col_version, self.source_repository)
                        metadata = self.extract_collections_metadata(install_msg, sub_download_location)
                        metadata_file = self.export_data(metadata, sub_download_location, download_metadata_file)
                        md = self.find_target_metadata(LoadType.COLLECTION, metadata_file, col_name)
                        if md:
                            self.install_galaxy_collection_from_reqfile(md.requirements_file, sub_dependency_dir_path)
                        # self.install_galaxy_collection_from_targz(md.download_src_path, sub_dependency_dir_path)
                    if md is not None:
                        downloaded_dep.metadata = md
                    downloaded_dep.metadata.source_repository = self.source_repository
                    parts = col_name.split(".")
                    fullpath = os.path.join(sub_dependency_dir_path, "ansible_collections", parts[0], parts[1])
                    downloaded_dep.dir = fullpath.replace(f"{self.root_dir}/", "")
                self.dependency_dirs.append(asdict(downloaded_dep))

        if role_dependencies:
            for rdep in role_dependencies:
                target_version = None
                if isinstance(rdep, dict):
                    rdep_name = rdep.get("name", None)
                    target_version = rdep.get("version", None)
                    if not rdep_name:
                        rdep_name = rdep.get("role", None)
                    rdep = rdep_name
                name = rdep
                if type(rdep) is dict:
                    name = rdep.get("name", "")
                    if name == "":
                        name = rdep.get("src", "")
                logger.debug("prepare dir for {}".format(name))
                downloaded_dep = Dependency(
                    name=name,
                )
                downloaded_dep.metadata.type = LoadType.ROLE
                downloaded_dep.metadata.name = name
                downloaded_dep.metadata.cache_enabled = cache_enabled
                # sub_dependency_dir_path = "{}/{}".format(dependency_dir_path, rdep)

                sub_dependency_dir_path = os.path.join(
                    self.dependency_dir_path,
                    "roles",
                    "src",
                    name,
                )

                if not os.path.exists(sub_dependency_dir_path):
                    os.makedirs(sub_dependency_dir_path)
                if cache_enabled:
                    logger.debug("cache enabled")
                    cache_dir_path = os.path.join(
                        cache_dir,
                        "roles",
                        name,
                    )
                    download_meta_dir_path = os.path.join(
                        cache_dir,
                        "roles_download_meta",
                        name,
                    )
                    if os.path.exists(cache_dir_path) and len(os.listdir(cache_dir_path)) != 0:
                        logger.debug("dependency cache data found")
                        metadata_file = os.path.join(download_meta_dir_path, download_metadata_file)
                        md = self.find_target_metadata(LoadType.ROLE, metadata_file, name)
                        self.move_src(cache_dir_path, sub_dependency_dir_path)
                    else:
                        logger.debug("dependency cache data not found")
                        install_msg = install_galaxy_target(name, LoadType.ROLE, sub_dependency_dir_path, self.source_repository, target_version)
                        logger.debug("role install msg: {}".format(install_msg))
                        metadata = self.extract_roles_metadata(install_msg)
                        if not metadata:
                            raise ValueError("failed to install {} {}".format(LoadType.ROLE, name))
                        metadata_file = self.export_data(metadata, download_meta_dir_path, download_metadata_file)
                        md = self.find_target_metadata(LoadType.ROLE, metadata_file, name)
                        # save cache
                        if not os.path.exists(cache_dir_path):
                            os.makedirs(cache_dir_path)
                        self.move_src(sub_dependency_dir_path, cache_dir_path)
                    if md:
                        downloaded_dep.metadata = md
                elif name in role_dependency_dirs:
                    logger.debug("use the specified dependency dirs")
                    sub_dependency_dir_path = role_dependency_dirs[name]
                else:
                    install_msg = install_galaxy_target(name, LoadType.ROLE, sub_dependency_dir_path, self.source_repository)
                    logger.debug("role install msg: {}".format(install_msg))
                    metadata = self.extract_roles_metadata(install_msg)
                    if not metadata:
                        raise ValueError("failed to install {} {}".format(LoadType.ROLE, name))
                    sub_download_location = os.path.join(self.download_location, "role", name)
                    metadata_file = self.export_data(metadata, sub_download_location, download_metadata_file)
                    md = self.find_target_metadata(LoadType.ROLE, metadata_file, name)
                    if md is not None:
                        downloaded_dep.metadata = md
                downloaded_dep.metadata.source_repository = self.source_repository
                self.dependency_dirs.append(asdict(downloaded_dep))
        return

    def src_install(self):
        try:
            self.setup_tmp_dir()
            self.root_install(self.tmp_install_dir)
        finally:
            self.clean_tmp_dir()
        return

    def root_install(self, tmp_src_dir):
        tmp_src_dir = os.path.join(self.tmp_install_dir.name, "src")
        if not os.path.exists(tmp_src_dir):
            os.makedirs(tmp_src_dir)

        logger.debug("root type is {}".format(self.target_type))
        if self.target_type == LoadType.PROJECT:
            # install_type = "github"
            # ansible-galaxy install
            if not self.silent:
                print("cloning {} from github".format(self.target_name))
            install_msg = install_github_target(self.target_name, tmp_src_dir)
            if not self.silent:
                logger.debug("STDOUT: {}".format(install_msg))
            # if self.target_dependency_dir == "":
            #     raise ValueError("dependency dir is required for project type")
            dependency_dir = self.target_dependency_dir
            dst_src_dir = os.path.join(self.target_path_mappings["src"], escape_url(self.target_name))
            self.metadata.download_url = self.target_name
        elif self.target_type == LoadType.COLLECTION:
            install_msg = ""
            sub_download_location = os.path.join(self.download_location, "collection", self.target_name)
            is_exist, targz_file = self.is_download_file_exist(LoadType.COLLECTION, self.target_name, self.download_location)
            if is_exist:
                metadata_file = os.path.join(targz_file.rsplit("/", 1)[0], download_metadata_file)
                md = self.find_target_metadata(LoadType.COLLECTION, metadata_file, self.target_name)
            else:
                install_msg = self.download_galaxy_collection(self.target_name, sub_download_location, version=self.target_version)
                metadata = self.extract_collections_metadata(install_msg, sub_download_location)
                metadata_file = self.export_data(metadata, sub_download_location, download_metadata_file)
                md = self.find_target_metadata(LoadType.COLLECTION, metadata_file, self.target_name)
            if md:
                self.install_galaxy_collection_from_reqfile(md.requirements_file, tmp_src_dir)
            dst_src_dir = self.target_path_mappings["src"]
            dependency_dir = tmp_src_dir
            self.metadata = md
        elif self.target_type == LoadType.ROLE:
            install_msg = ""
            sub_download_location = os.path.join(self.download_location, "roles", self.target_name)
            metafile_location = os.path.join(self.download_location, "roles_download_meta", self.target_name)
            if os.path.exists(sub_download_location) and len(os.listdir(sub_download_location)) != 0:
                logger.debug("found cache data {}".format(sub_download_location))
                metadata_file = os.path.join(metafile_location, download_metadata_file)
                md = self.find_target_metadata(LoadType.ROLE, metadata_file, self.target_name)
                tmp_target_dir = os.path.join(tmp_src_dir, self.target_name)
                if not os.path.exists(tmp_target_dir):
                    os.makedirs(tmp_target_dir)
                self.move_src(sub_download_location, tmp_target_dir)
            else:
                install_msg = install_galaxy_target(
                    self.target_name, self.target_type, tmp_src_dir, self.source_repository, target_version=self.target_version
                )
                logger.debug("role install msg: {}".format(install_msg))
                metadata = self.extract_roles_metadata(install_msg)
                if not metadata:
                    raise ValueError("failed to install {} {}".format(self.target_type, self.target_name))
                metadata_file = self.export_data(metadata, metafile_location, download_metadata_file)
                md = self.find_target_metadata(LoadType.ROLE, metadata_file, self.target_name)
                # save cache
                if not os.path.exists(sub_download_location):
                    os.makedirs(sub_download_location)
                self.move_src(tmp_src_dir, sub_download_location)
            if not md:
                raise ValueError("failed to install {} {}".format(self.target_type, self.target_name))
            dependency_dir = tmp_src_dir
            dst_src_dir = self.target_path_mappings["src"]
            self.metadata.download_src_path = "{}.{}".format(dst_src_dir, self.target_name)
            self.metadata = md
        else:
            raise ValueError("unsupported container type")

        self.install_log = install_msg
        if self.do_save:
            self.__save_install_log()

        self.set_index(dependency_dir)

        if not self.silent:
            print("moving index")
            logger.debug("index: {}".format(json.dumps(self.index)))
        if self.do_save:
            self.__save_index()
        if not os.path.exists(dst_src_dir):
            os.makedirs(dst_src_dir)
        self.move_src(tmp_src_dir, dst_src_dir)
        root_dst_src_path = "{}/{}".format(dst_src_dir, self.target_name)
        if self.target_type == LoadType.ROLE:
            self.update_role_download_src(metadata_file, dst_src_dir)
            self.metadata.download_src_path = root_dst_src_path
            self.metadata.metafile_path, _ = self.get_metafile_in_target(self.target_type, root_dst_src_path)
            self.metadata.author = self.get_author(self.target_type, self.metadata.metafile_path)

        if self.target_type == LoadType.PROJECT and self.target_dependency_dir:
            dst_dependency_dir = self.target_path_mappings["dependencies"]
            if not os.path.exists(dst_dependency_dir):
                os.makedirs(dst_dependency_dir)
            self.move_src(dependency_dir, dst_dependency_dir)
            logger.debug("root metadata: {}".format(json.dumps(asdict(self.metadata))))

        # prepare dependency data
        self.dependency_dirs = self.dependnecy_dirs(metadata_file, self.target_type, self.target_name)
        return

    def set_index(self, path):
        if not self.silent:
            print("crawl content")
        dep_type = LoadType.UNKNOWN
        target_path_list = []
        if os.path.isfile(path):
            # need further check?
            dep_type = LoadType.PLAYBOOK
            target_path_list.append = [path]
        elif os.path.exists(os.path.join(path, collection_manifest_json)):
            dep_type = LoadType.COLLECTION
            target_path_list = [path]
        elif os.path.exists(os.path.join(path, role_meta_main_yml)):
            dep_type = LoadType.ROLE
            target_path_list = [path]
        else:
            dep_type, target_path_list = find_ext_dependencies(path)

        if not self.silent:
            logger.info('the detected target type: "{}", found targets: {}'.format(self.target_type, len(target_path_list)))

        if self.target_type not in supported_target_types:
            logger.error("this target type is not supported")
            sys.exit(1)

        list = []
        for target_path in target_path_list:
            ext_name = get_target_name(dep_type, target_path)
            list.append(
                {
                    "name": ext_name,
                    "type": dep_type,
                }
            )

        index_data = {
            "dependencies": list,
            "path_mappings": self.target_path_mappings,
        }

        self.index = index_data

    def download_galaxy_collection(self, target, output_dir, version="", source_repository=""):
        server_option = ""
        if source_repository:
            server_option = "--server {}".format(source_repository)
        target_version = target
        if version:
            target_version = "{}:{}".format(target, version)
        logger.debug("downloading: {}".format("ansible-galaxy collection download '{}' {} -p {}".format(target_version, server_option, output_dir)))
        proc = subprocess.run(
            "ansible-galaxy collection download '{}' {} -p {}".format(target_version, server_option, output_dir),
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        install_msg = proc.stdout
        logger.debug("STDOUT: {}".format(install_msg))
        return install_msg

    def download_galaxy_collection_from_reqfile(self, requirements, output_dir, source_repository=""):
        server_option = ""
        if source_repository:
            server_option = "--server {}".format(source_repository)
        proc = subprocess.run(
            "ansible-galaxy collection download -r {} {} -p {}".format(requirements, server_option, output_dir),
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        install_msg = proc.stdout
        logger.debug("STDOUT: {}".format(install_msg))
        # return proc.stdout

    def install_galaxy_collection_from_targz(self, tarfile, output_dir):
        logger.debug("install collection from {}".format(tarfile))
        proc = subprocess.run(
            "ansible-galaxy collection install {} -p {}".format(tarfile, output_dir),
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        install_msg = proc.stdout
        logger.debug("STDOUT: {}".format(install_msg))
        # return proc.stdout

    def install_galaxy_collection_from_reqfile(self, requirements, output_dir):
        if not os.path.isfile(requirements):
            # get requirements file from archives dir under current root_dir
            child_dir_path = requirements.split("archives")[-1]
            requirements = f"{self.download_location}{child_dir_path}"
            if not os.path.isfile(requirements):
                logger.warning("requirements file not found: {}".format(requirements))
                return
        logger.debug("install collection from {}".format(requirements))
        src_dir = requirements.replace(requirements_yml, "")
        proc = subprocess.run(
            "cd {} && ansible-galaxy collection install -r {} -p {}".format(src_dir, requirements, output_dir),
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        try:
            proc.check_returncode()
        except Exception as exc:
            raise ValueError("failed to install collection: " + proc.stderr) from exc
        install_msg = proc.stdout
        logger.debug("STDOUT: {}".format(install_msg))
        # return proc.stdout

    def is_download_file_exist(self, type, target, dir):
        is_exist = False
        filename = ""
        download_metadata_files = glob.glob(f"{dir}/{type}/{target}/**/{download_metadata_file}", recursive=True)
        # check if tar.gz file already exists
        if len(download_metadata_files) != 0:
            for metafile in download_metadata_files:
                md = self.find_target_metadata(type, metafile, target)
                if md is not None:
                    is_exist = True
                    filename = md.download_src_path
        else:
            if os.path.exists(dir):
                namepart = target.replace(".", "-")
                for file in os.listdir(dir):
                    if file.endswith(".tar.gz") and namepart in file:
                        is_exist = True
                        filename = file
        return is_exist, filename

    def install_galaxy_role_from_reqfile(self, file, output_dir):
        proc = subprocess.run(
            "ansible-galaxy role install -r {} -p {}".format(file, output_dir),
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        install_msg = proc.stdout
        logger.debug("STDOUT: {}".format(install_msg))

    def extract_collections_metadata(self, log_message, download_location):
        # -- log message
        # Downloading collection 'community.rabbitmq:1.2.3' to
        # Downloading https://galaxy.ansible.com/download/ansible-posix-1.4.0.tar.gz to ...
        download_url_pattern = r"Downloading (.*) to"
        url = ""
        version = ""
        hash = ""
        match_messages = re.findall(download_url_pattern, log_message)
        download_path_from_root_dir = download_location.replace(f"{self.root_dir}/", "")
        metadata_list = []
        for m in match_messages:
            metadata = DownloadMetadata()
            metadata.type = LoadType.COLLECTION
            if m.endswith("tar.gz"):
                logger.debug("extracted url from download log message: {}".format(m))
                url = m
                version = url.split("-")[-1].replace(".tar.gz", "")
                name = "{}.{}".format(url.split("-")[0].split("/")[-1], url.split("-")[1])
                metadata.download_url = url
                metadata.version = version
                metadata.name = name
                filename = url.split("/")[-1]
                fullpath = "{}/{}".format(download_location, filename)
                if not os.path.exists(fullpath):
                    logger.warning("failed to get metadata for {}".format(url))
                    pass
                m_time = os.path.getmtime(fullpath)
                dt_m = datetime.datetime.utcfromtimestamp(m_time).isoformat()
                metadata.download_timestamp = dt_m
                metadata.download_src_path = fullpath.replace(download_location, download_path_from_root_dir)
                metafile_path, files_json_path = self.get_metafile_in_target(LoadType.COLLECTION, fullpath)
                metadata.metafile_path = metafile_path.replace(download_location, download_path_from_root_dir)
                metadata.files_json_path = files_json_path.replace(download_location, download_path_from_root_dir)
                metadata.author = self.get_author(LoadType.COLLECTION, metadata.metafile_path)
                metadata.requirements_file = "{}/{}".format(download_path_from_root_dir, requirements_yml)

                if url != "":
                    hash = get_hash_of_url(url)
                    metadata.hash = hash
                logger.debug("metadata: {}".format(json.dumps(asdict(metadata))))

                metadata_list.append(asdict(metadata))
        result = {"collections": metadata_list}
        return result

    def extract_roles_metadata(self, log_message):
        # - downloading role from https://github.com/rhythmictech/ansible-role-awscli/archive/1.0.3.tar.gz
        # - extracting rhythmictech.awscli to /private/tmp/role-test/rhythmictech.awscli
        url = ""
        version = ""
        hash = ""
        metadata_list = []
        messages = log_message.splitlines()
        for i, line in enumerate(messages):
            if line.startswith("- downloading role from "):
                metadata = DownloadMetadata()
                metadata.type = LoadType.ROLE
                url = line.split(" ")[-1]
                logger.debug("extracted url from download log message: {}".format(url))
                version = url.split("/")[-1].replace(".tar.gz", "")
                if len(messages) > i:
                    name = messages[i + 1].split("/")[-1]
                    metadata.download_url = url
                    metadata.version = version
                    metadata.name = name
                    role_dir = messages[i + 1].split(" ")[-1]
                    m_time = os.path.getmtime(role_dir)
                    dt_m = datetime.datetime.utcfromtimestamp(m_time).isoformat()
                    metadata.download_timestamp = dt_m
                    metadata.download_src_path = role_dir.replace(f"{self.root_dir}/", "")
                    if url != "":
                        hash = get_hash_of_url(url)
                        metadata.hash = hash
                    logger.debug("metadata: {}".format(json.dumps(asdict(metadata))))
                    metadata_list.append(asdict(metadata))
        if len(metadata_list) == 0:
            logger.warning(f"failed to extract download metadata from install log: {log_message}")
            return None
        result = {"roles": metadata_list}
        return result

    def find_target_metadata(self, type, metadata_file, target):
        if not os.path.isfile(metadata_file):
            # get metadata file from archives dir under current root_dir
            child_dir_path = metadata_file.split("archives")[-1]
            metadata_file = f"{self.download_location}{child_dir_path}"
            if not os.path.isfile(metadata_file):
                logger.warning("metadata file not found: {}".format(target))
                return None
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        if type == LoadType.COLLECTION:
            metadata_list = metadata.get("collections", [])
        elif type == LoadType.ROLE:
            metadata_list = metadata.get("roles", [])
        else:
            logger.warning("metadata not found: unsupported type {} {}".format(type, target))
            return None
        for data in metadata_list:
            dm = DownloadMetadata(**data)
            if dm.name == target:
                logger.debug("found metadata: {}".format(target))
                return dm
        logger.warning("metadata not found: {}".format(target))
        return None

    def existing_dependency_dir_loader(self, dependency_type, dependency_dir_path):
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

    def __save_install_log(self):
        tmpdir = self.tmp_install_dir.name
        tmp_install_log = os.path.join(tmpdir, "install.log")
        with open(tmp_install_log, "w") as f:
            f.write(self.install_log)

    def __save_index(self):
        index_location = self.__path_mappings["index"]
        index_dir = os.path.dirname(os.path.abspath(index_location))
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        with open(index_location, "w") as f:
            json.dump(self.index, f, indent=2)

    def move_src(self, src, dst):
        if src == "" or not os.path.exists(src) or not os.path.isdir(src):
            raise ValueError("src {} is not directory".format(src))
        if dst == "" or ".." in dst:
            raise ValueError("dst {} is invalid".format(dst))
        # we use cp command here because shutil module is slow,
        # but the behavior of cp command is slightly different between Mac and Linux
        # we use a command like `cp -r <src>/* <dst>/` so the behavior will be the same
        dirs = os.listdir(src)
        proc = subprocess.run(
            f"cp -r {src}/* {dst}/",
            shell=True,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        # raise if copy failed
        try:
            proc.check_returncode()
        except Exception as exc:
            raise ValueError(proc.stderr + "\ndirs: " + ", ".join(dirs)) from exc
        return

    def setup_tmp_dir(self):
        if self.tmp_install_dir is None or not os.path.exists(self.tmp_install_dir.name):
            self.tmp_install_dir = tempfile.TemporaryDirectory()
            if self.periodical_cleanup:
                self.cleanup_queue.append(deepcopy(self.tmp_install_dir))

    def clean_tmp_dir(self):
        if self.tmp_install_dir is not None and os.path.exists(self.tmp_install_dir.name):
            if self.periodical_cleanup:
                if len(self.cleanup_queue) > self.cleanup_threshold:
                    for tmp_dir in self.cleanup_queue:
                        try:
                            tmp_dir.cleanup()
                        except Exception:
                            pass
                    self.cleanup_queue = []
            else:
                self.tmp_install_dir.cleanup()
                self.tmp_install_dir = None

    def export_data(self, data, dir, filename):
        if not os.path.exists(dir):
            os.makedirs(dir)
        file = os.path.join(dir, filename)
        logger.debug("export data {} to {}".format(data, file))
        with open(file, "w") as f:
            json.dump(data, f)
        return file

    def get_metafile_in_target(self, type, filepath):
        metafile_path = ""
        files_path = ""
        if type == LoadType.COLLECTION:
            # get manifest.json
            with tarfile.open(name=filepath, mode="r") as tar:
                for info in tar.getmembers():
                    if info.name.endswith(collection_manifest_json):
                        f = tar.extractfile(info)
                        metafile_path = filepath.replace(".tar.gz", "-{}".format(collection_manifest_json))
                        with open(metafile_path, "wb") as c:
                            c.write(f.read())
                    if info.name.endswith(collection_files_json):
                        f = tar.extractfile(info)
                        files_path = filepath.replace(".tar.gz", "-{}".format(collection_files_json))
                        with open(files_path, "wb") as c:
                            c.write(f.read())
        elif type == LoadType.ROLE:
            # get meta/main.yml path
            role_meta_files = safe_glob(
                [
                    os.path.join(filepath, "**", role_meta_main_yml),
                    os.path.join(filepath, "**", role_meta_main_yaml),
                ],
                recursive=True,
            )
            if len(role_meta_files) != 0:
                metafile_path = role_meta_files[0]
        return metafile_path, files_path

    def update_metadata(self, type, metadata_file, target, key, value):
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        if type == LoadType.COLLECTION:
            metadata_list = metadata.get("collections", [])
        elif type == LoadType.ROLE:
            metadata_list = metadata.get("roles", [])
        else:
            logger.warning("metadata not found: unsupported type {}".format(target))
            return None
        for i, data in enumerate(metadata_list):
            dm = DownloadMetadata(**data)
            if dm.name == target:
                if hasattr(dm, key):
                    setattr(dm, key, value)
                metadata_list[i] = asdict(dm)
                logger.debug("update {} in metadata: {}".format(key, dm))
                if type == LoadType.COLLECTION:
                    metadata["collections"] = metadata_list
                elif type == LoadType.ROLE:
                    metadata["roles"] = metadata_list
                with open(metadata_file, "w") as f:
                    json.dump(metadata, f)
        return

    def update_role_download_src(self, metadata_file, dst_src_dir):
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        metadata_list = metadata.get("roles", [])
        for i, data in enumerate(metadata_list):
            dm = DownloadMetadata(**data)
            full_path = "{}/{}".format(dst_src_dir, dm.name)
            path_from_root = full_path.replace(f"{self.root_dir}/", "")
            key = "download_src_path"
            if hasattr(dm, key):
                setattr(dm, key, path_from_root)
            metafile_path, _ = self.get_metafile_in_target(LoadType.ROLE, full_path)
            dm.metafile_path = metafile_path.replace(f"{self.root_dir}/", "")
            dm.author = self.get_author(LoadType.ROLE, metafile_path)
            metadata_list[i] = asdict(dm)
            logger.debug("update {} in metadata: {}".format(key, dm))
        metadata["roles"] = metadata_list
        with open(metadata_file, "w") as f:
            json.dump(metadata, f)
        return

    def get_author(self, type, metafile_path):
        if not os.path.exists(metafile_path):
            metafile_path = f"{self.root_dir}/{metafile_path}"
            if not os.path.exists(metafile_path):
                logger.warning("invalid file path: {}".format(metafile_path))
                return ""
        if type == LoadType.COLLECTION:
            with open(metafile_path, "r") as f:
                metadata = json.load(f)
            authors = metadata.get("collection_info", {}).get("authors", [])
            return ",".join(authors)
        elif type == LoadType.ROLE:
            with open(metafile_path, "r") as f:
                metadata = yaml.safe_load(f)
            author = metadata.get("galaxy_info", {}).get("author", "")
            return author

    def dependnecy_dirs(self, metadata_file, target_type, target_name):
        dependency_dirs = []
        if not os.path.isfile(metadata_file):
            # get metadata file from archives dir under current root_dir
            child_dir_path = metadata_file.split("archives")[-1]
            metadata_file = f"{self.download_location}{child_dir_path}"
            if not os.path.isfile(metadata_file):
                logger.warning("metadata file not found: {}".format(target_name))
                return dependency_dirs
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        metadata_list = metadata.get("roles", [])
        for _, data in enumerate(metadata_list):
            dm = DownloadMetadata(**data)
            downloaded_dep = Dependency(
                name=dm.name,
                metadata=dm,
            )
            downloaded_dep.dir = os.path.join(dm.download_src_path)
            if target_type == LoadType.ROLE and target_name == dm.name:
                continue
            dependency_dirs.append(asdict(downloaded_dep))

        metadata_list = metadata.get("collections", [])
        for _, data in enumerate(metadata_list):
            dm = DownloadMetadata(**data)
            downloaded_dep = Dependency(
                name=dm.name,
                metadata=dm,
            )
            parts = dm.name.split(".")
            full_path = os.path.join(self.target_path_mappings["src"], "ansible_collections", parts[0], parts[1])
            downloaded_dep.dir = full_path.replace(f"{self.root_dir}/", "")
            if target_type == LoadType.COLLECTION and target_name == dm.name:
                continue
            dependency_dirs.append(asdict(downloaded_dep))
        return dependency_dirs


def find_ext_dependencies(path):
    collection_meta_files = safe_glob(os.path.join(path, "**", collection_manifest_json), recursive=True)
    if len(collection_meta_files) > 0:
        collection_path_list = [trim_suffix(f, ["/" + collection_manifest_json]) for f in collection_meta_files]
        collection_path_list = remove_subdirectories(collection_path_list)
        return LoadType.COLLECTION, collection_path_list
    role_meta_files = safe_glob(
        [
            os.path.join(path, "**", role_meta_main_yml),
            os.path.join(path, "**", role_meta_main_yaml),
        ],
        recursive=True,
    )
    if len(role_meta_files) > 0:
        role_path_list = [trim_suffix(f, ["/" + role_meta_main_yml, "/" + role_meta_main_yaml]) for f in role_meta_files]
        role_path_list = remove_subdirectories(role_path_list)
        return LoadType.ROLE, role_path_list
    return LoadType.UNKNOWN, []
