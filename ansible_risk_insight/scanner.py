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
import sys
import copy
import shutil
import json
import tempfile
import logging
import jsonpickle
from dataclasses import dataclass, field
from .models import (
    Load,
    LoadType,
    ObjectList,
    TaskCallsInTree,
)

from .loader import (
    get_loader_version,
    get_target_name,
    remove_subdirectories,
    trim_suffix,
)
from .parser import Parser
from .model_loader import load_object, find_playbook_role_module
from .safe_glob import safe_glob
from .tree import TreeLoader
from .annotators.variable_resolver import resolve_variables
from .analyzer import analyze
from .risk_detector import detect
from .dependency_dir_preparator import (
    dependency_dir_preparator,
)
from .findings import Findings
from .fm_db import FMDBClient
from .utils import (
    escape_url,
    install_galaxy_target,
    install_github_target,
    get_download_metadata,
    get_installed_metadata,
    get_hash_of_url,
)


class Config:
    data_dir: str = os.environ.get("ARI_DATA_DIR", os.path.join("/tmp", "ari-data"))
    log_level: str = os.environ.get("ARI_LOG_LEVEL", "info").lower()


collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"

log_level_map = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}

supported_target_types = [
    LoadType.PROJECT,
    LoadType.COLLECTION,
    LoadType.ROLE,
    LoadType.PLAYBOOK,
]

config = Config()


logging.basicConfig()
logging.getLogger().setLevel(log_level_map[config.log_level])


@dataclass
class ARIScanner(object):
    type: str = ""
    name: str = ""
    id: str = ""

    install_log: str = ""
    tmp_install_dir: tempfile.TemporaryDirectory = None

    index: dict = field(default_factory=dict)

    root_definitions: dict = field(default_factory=dict)
    ext_definitions: dict = field(default_factory=dict)

    trees: list = field(default_factory=list)
    # for inventory object
    additional: ObjectList = ObjectList()

    taskcalls_in_trees: list = field(default_factory=list)

    report_to_display: str = ""
    data_report: dict = field(default_factory=dict)

    # TODO: remove attributes below once refactoring is done
    root_dir: str = ""
    __path_mappings: dict = field(default_factory=dict)

    dependency_dir: str = ""
    target_path: str = ""
    loaded_dependency_dirs: list = field(default_factory=list)

    prm: dict = field(default_factory=dict)

    fm_db_client: FMDBClient = None

    do_save: bool = False
    _parser: Parser = None

    download_url: str = ""
    version: str = ""
    hash: str = ""

    source_repository: str = ""
    out_dir: str = ""
    pretty: bool = False
    silent: bool = False

    findings: Findings = None

    def __post_init__(self):
        if self.type == LoadType.COLLECTION or self.type == LoadType.ROLE:
            type_root = self.type + "s"
            self.__path_mappings = {
                "src": os.path.join(self.root_dir, type_root, "src"),
                "root_definitions": os.path.join(
                    self.root_dir,
                    type_root,
                    "root",
                    "definitions",
                    type_root,
                    self.name,
                ),
                "ext_definitions": {
                    LoadType.ROLE: os.path.join(self.root_dir, "roles", "definitions"),
                    LoadType.COLLECTION: os.path.join(self.root_dir, "collections", "definitions"),
                },
                "index": os.path.join(
                    self.root_dir,
                    type_root,
                    "{}-{}-index-ext.json".format(self.type, self.name),
                ),
                "install_log": os.path.join(
                    self.root_dir,
                    type_root,
                    "{}-{}-install.log".format(self.type, self.name),
                ),
            }

        elif self.type == LoadType.PROJECT:
            type_root = self.type + "s"
            proj_name = escape_url(self.name)
            self.__path_mappings = {
                "src": os.path.join(self.root_dir, type_root, proj_name, "src"),
                "root_definitions": os.path.join(
                    self.root_dir,
                    type_root,
                    proj_name,
                    "definitions",
                ),
                "ext_definitions": {
                    LoadType.ROLE: os.path.join(self.root_dir, "roles", "definitions"),
                    LoadType.COLLECTION: os.path.join(self.root_dir, "collections", "definitions"),
                },
                "index": os.path.join(
                    self.root_dir,
                    type_root,
                    proj_name,
                    "index-ext.json",
                ),
                "install_log": os.path.join(
                    self.root_dir,
                    type_root,
                    proj_name,
                    "{}-{}-install.log".format(self.type, proj_name),
                ),
                "dependencies": os.path.join(self.root_dir, type_root, proj_name, "dependencies"),
            }

        else:
            raise ValueError("Unsupported type: {}".format(self.type))

        self.fm_db_client = FMDBClient(root_dir=self.root_dir)

    def prepare_dependencies(self, root_install=False):
        # Install the target if needed
        target_path = self.make_target_path(self.type, self.name)
        if self.is_src_installed():
            pass
        else:
            if root_install:
                self.download_url, self.version, self.hash = self.src_install()
                if not self.silent:
                    logging.debug("install() done")
            else:
                self.download_url, self.version = get_installed_metadata(self.type, self.name, target_path)
                self.hash = get_hash_of_url(self.download_url)

        # Dependency Dir Preparator
        dep_dirs = dependency_dir_preparator(self.type, target_path, self.dependency_dir, self.root_dir, source_repository=self.source_repository)

        self.target_path = target_path
        self.loaded_dependency_dirs = dep_dirs

        return target_path, dep_dirs

    def load(self, prepare_dependencies=False):

        if prepare_dependencies:
            self.prepare_dependencies()

        ext_list = []
        ext_list.extend(
            [
                (
                    d.get("metadata", {}).get("type", ""),
                    d.get("metadata", {}).get("name", ""),
                    d.get("metadata", {}).get("version", ""),
                    d.get("metadata", {}).get("hash", ""),
                    d.get("dir"),
                )
                for d in self.loaded_dependency_dirs
            ]
        )
        ext_count = len(ext_list)

        # PRM Finder
        playbooks, roles, modules = find_playbook_role_module(self.target_path)
        self.prm["playbooks"] = playbooks
        self.prm["roles"] = roles
        self.prm["modules"] = modules

        # Start ARI Scanner main flow
        self._parser = Parser()
        for i, (ext_type, ext_name, ext_ver, ext_hash, ext_path) in enumerate(ext_list):
            if not self.silent:
                if i == 0:
                    logging.info("start loading {} {}(s)".format(ext_count, ext_type))
                logging.info("[{}/{}] {} {}".format(i + 1, ext_count, ext_type, ext_name))

            # avoid infinite loop
            is_root = False
            if self.type == ext_type and self.name == ext_name:
                is_root = True

            if not is_root:
                # scan dependencies and save findings to ARI FM
                dep_scanner = ARIScanner(
                    type=ext_type,
                    name=ext_name,
                    version=ext_ver,
                    hash=ext_hash,
                    target_path=ext_path,
                    root_dir=self.root_dir,
                    dependency_dir=self.dependency_dir,
                    do_save=self.do_save,
                    source_repository=self.source_repository,
                    silent=True,
                )
                # use prepared dep dirs
                dep_scanner.load(prepare_dependencies=False)

                # seatching findings from ARI FM and use them if found
                key = "{}-{}".format(self.type, self.name)
                loaded, self.ext_definitions[key] = self.load_definitions_from_findings(ext_type, ext_name, ext_ver, ext_hash)
                if loaded:
                    print("[DEBUG] Use spec data in FM DB")
                    continue

                # load the src directory
                self.load_definition_ext(ext_type, ext_name, ext_path)

        if not self.silent:
            logging.debug("load_definition_ext() done")

        loaded, self.root_definitions = self.load_definitions_from_findings(self.type, self.name, self.version, self.hash)
        if loaded:
            if not self.silent:
                print("[DEBUG] Use spec data in FM DB")
        else:
            self.load_definitions_root()

        if not self.silent:
            logging.debug("load_definitions_root() done")

        self.set_trees()
        if not self.silent:
            logging.debug("set_trees() done")
        self.set_resolved()
        if not self.silent:
            logging.debug("set_resolved() done")
        self.set_analyzed()
        if not self.silent:
            logging.debug("set_analyzed() done")
        self.set_report()
        if not self.silent:
            logging.debug("set_report() done")
        dep_num, ext_counts, root_counts = self.count_definitions()
        if not self.silent:
            print("# of dependencies:", dep_num)
            print("ext definitions:", ext_counts)
            print("root definitions:", root_counts)

        self.register_findings_to_fm()

        if self.out_dir is not None and self.out_dir != "":
            self.save_findings(out_dir=self.out_dir)
            if not self.silent:
                print("The findings are saved at {}".format(self.out_dir))

        if not self.silent:
            print("-" * 60)
            print("ARI scan completed!")
            print(f"Findings have been saved at: {self.fm_db_client.make_findings_dir_path(self.type, self.name, self.version, self.hash)}")

        if self.pretty:
            if not self.silent:
                print(json.dumps(self.findings.showable(), indent=2))

        return

    def make_target_path(self, typ, target_name):
        target_path = ""
        if typ == LoadType.COLLECTION:
            parts = target_name.split(".")
            target_path = os.path.join(self.root_dir, typ + "s", "src", "ansible_collections", parts[0], parts[1])
        elif typ == LoadType.ROLE:
            target_path = os.path.join(self.root_dir, typ + "s", "src", target_name)
        elif typ == LoadType.PROJECT:
            target_path = os.path.join(self.get_src_root(), escape_url(target_name))
        return target_path

    def get_src_root(self):
        return self.__path_mappings["src"]

    def is_src_installed(self):
        index_location = self.__path_mappings["index"]
        return os.path.exists(index_location)

    def load_index(self):
        index_location = self.__path_mappings["index"]
        with open(index_location, "r") as f:
            self.index = json.load(f)

    def __save_index(self):
        index_location = self.__path_mappings["index"]
        index_dir = os.path.dirname(os.path.abspath(index_location))
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        with open(index_location, "w") as f:
            json.dump(self.index, f, indent=2)

    def get_ext_list(self):
        dep_list = self.index.get("dependencies", [])
        ext_list = []
        for dep in dep_list:
            ext_type = dep.get("type", "")
            ext_name = dep.get("name", "")
            if ext_type != "" and ext_name != "":
                ext_list.append((ext_type, ext_name))
        return ext_list

    def src_install(self):
        download_url = ""
        version = ""
        hash = ""
        try:
            self.setup_tmp_dir()
            download_url, version, hash = self.install()
        finally:
            self.clean_tmp_dir()
        return download_url, version, hash

    def install(self):
        tmp_src_dir = os.path.join(self.tmp_install_dir.name, "src")

        install_msg = ""
        dependency_dir = ""
        dst_src_dir = ""

        download_url = ""
        version = ""
        hash = ""

        if self.type in [LoadType.COLLECTION, LoadType.ROLE]:
            # install_type = "galaxy"
            # ansible-galaxy install
            if not self.silent:
                print("installing a {} <{}> from galaxy".format(self.type, self.name))
            install_msg = install_galaxy_target(self.name, self.type, tmp_src_dir, self.source_repository)
            if not self.silent:
                logging.debug("STDOUT: {}".format(install_msg))
            dependency_dir = tmp_src_dir
            dst_src_dir = self.get_src_root()
            download_url, version, hash = get_download_metadata(typ=self.type, install_msg=install_msg)

        elif self.type == LoadType.PROJECT:
            # install_type = "github"
            # ansible-galaxy install
            if not self.silent:
                print("cloning {} from github".format(self.name))
            install_msg = install_github_target(self.name, self.type, tmp_src_dir)
            if not self.silent:
                logging.debug("STDOUT: {}".format(install_msg))
            if self.dependency_dir == "":
                raise ValueError("dependency dir is required for project type")
            dependency_dir = self.dependency_dir
            dst_src_dir = os.path.join(self.get_src_root(), escape_url(self.name))
            download_url = self.name

        else:
            raise ValueError("unsupported container type")

        self.install_log = install_msg
        if self.do_save:
            self.__save_install_log()

        self.set_index(dependency_dir)

        if not self.silent:
            print("moving index")
            logging.debug("index: {}".format(json.dumps(self.index)))
        if self.do_save:
            self.__save_index()
        if not os.path.exists(dst_src_dir):
            os.makedirs(dst_src_dir)
        self.move_src(tmp_src_dir, dst_src_dir)

        if self.type == LoadType.PROJECT:
            dst_dependency_dir = self.__path_mappings["dependencies"]
            if not os.path.exists(dst_dependency_dir):
                os.makedirs(dst_dependency_dir)
            self.move_src(dependency_dir, dst_dependency_dir)

        return download_url, version, hash

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
            logging.info('the detected target type: "{}", found targets: {}'.format(self.type, len(target_path_list)))

        if self.type not in supported_target_types:
            logging.error("this target type is not supported")
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
            "path_mappings": self.__path_mappings,
        }

        self.index = index_data

    def __save_install_log(self):
        tmpdir = self.tmp_install_dir.name
        tmp_install_log = os.path.join(tmpdir, "install.log")
        with open(tmp_install_log, "w") as f:
            f.write(self.install_log)

    def _get_target_list(self):
        dep_list = self.index.get("dependencies", [])
        target_list = []
        for dep in dep_list:
            ext_type = dep.get("type", "")
            ext_name = dep.get("name", "")
            target_path = self.get_source_path(ext_type, ext_name)
            target_list.append((ext_type, ext_name, target_path))
        return target_list

    def get_definition_path(self, ext_type, ext_name):
        target_path = ""
        if ext_type == LoadType.ROLE:
            target_path = os.path.join(
                self.__path_mappings["ext_definitions"][LoadType.ROLE],
                ext_name,
            )
        elif ext_type == LoadType.COLLECTION:
            target_path = os.path.join(
                self.__path_mappings["ext_definitions"][LoadType.COLLECTION],
                ext_name,
            )
        else:
            raise ValueError("Invalid ext_type")
        return target_path

    def get_source_path(self, ext_type, ext_name, is_ext_for_project=False):
        base_dir = ""
        if is_ext_for_project:
            base_dir = self.__path_mappings["dependencies"]
        else:
            if ext_type == LoadType.ROLE:
                base_dir = os.path.join(self.root_dir, "roles", "src")
            elif ext_type == LoadType.COLLECTION:
                base_dir = os.path.join(self.root_dir, "collections", "src")

        target_path = ""
        if ext_type == LoadType.ROLE:
            target_path = os.path.join(base_dir, ext_name)
        elif ext_type == LoadType.COLLECTION:
            parts = ext_name.split(".")
            target_path = os.path.join(
                base_dir,
                "ansible_collections",
                parts[0],
                parts[1],
            )
        else:
            raise ValueError("Invalid ext_type")
        return target_path

    def _set_load_root(self):
        root_load_data = None
        if self.type in [LoadType.ROLE, LoadType.COLLECTION]:
            ext_type = self.type
            ext_name = self.name
            target_path = self.get_source_path(ext_type, ext_name)
            root_load_data = self.create_load_file(ext_type, ext_name, target_path)
        elif self.type == LoadType.PROJECT:
            src_root = self.get_src_root()
            dst_src_dir = os.path.join(src_root, escape_url(self.name))
            root_load_data = self.create_load_file(self.type, self.name, dst_src_dir)
        return root_load_data

    def get_definitions(self):
        return self.root_definitions, self.ext_definitions

    def set_trees(self):
        trees, additional = tree(self.root_definitions, self.ext_definitions)
        self.trees = trees
        self.additional = additional

        if self.do_save:
            root_def_dir = self.__path_mappings["root_definitions"]
            tree_rel_file = os.path.join(root_def_dir, "tree.json")
            if tree_rel_file != "":
                lines = []
                for t_obj_list in self.trees:
                    lines.append(t_obj_list.to_one_line_json())
                open(tree_rel_file, "w").write("\n".join(lines))
                if not self.silent:
                    logging.info("  tree file saved")
        return

    def get_trees(self):
        return self.trees, self.node_objects

    def set_resolved(self):
        taskcalls_in_trees = resolve(self.trees, self.additional)
        self.taskcalls_in_trees = taskcalls_in_trees

        if self.do_save:
            root_def_dir = self.__path_mappings["root_definitions"]
            tasks_in_t_path = os.path.join(root_def_dir, "tasks_in_trees.json")
            tasks_in_t_lines = []
            for d in taskcalls_in_trees:
                line = jsonpickle.encode(d, make_refs=False)
                tasks_in_t_lines.append(line)

            open(tasks_in_t_path, "w").write("\n".join(tasks_in_t_lines))
        return

    def get_resolved(self):
        return self.taskcalls_in_trees

    def set_analyzed(self):
        taskcalls_in_trees = analyze(self.taskcalls_in_trees)
        self.taskcalls_in_trees = taskcalls_in_trees

        if self.do_save:
            root_def_dir = self.__path_mappings["root_definitions"]
            tasks_in_t_a_path = os.path.join(root_def_dir, "tasks_in_trees_with_analysis.json")
            tasks_in_t_a_lines = []
            for d in taskcalls_in_trees:
                line = jsonpickle.encode(d, make_refs=False)
                tasks_in_t_a_lines.append(line)

            open(tasks_in_t_a_path, "w").write("\n".join(tasks_in_t_a_lines))

        return

    def get_analyzed(self):
        return self.taskcalls_in_trees

    def set_report(self):
        coll_type = LoadType.COLLECTION
        coll_name = self.name if self.type == coll_type else ""
        report_txt, data_report = detect(self.taskcalls_in_trees, collection_name=coll_name)
        self.report_to_display = report_txt
        metadata = {
            "type": self.type,
            "name": self.name,
            "version": self.version,
            "source": self.source_repository,
            "download_url": self.download_url,
            "hash": self.hash,
        }
        dependencies = [d["metadata"] for d in self.loaded_dependency_dirs]

        self.findings = Findings(
            metadata=metadata,
            dependencies=dependencies,
            root_definitions=self.root_definitions,
            ext_definitions=self.ext_definitions,
            prm=self.prm,
            report=data_report,
        )
        return

    def get_report(self):
        return self.report_to_display

    def count_definitions(self):
        dep_num = len(self.loaded_dependency_dirs)
        ext_counts = {}
        for _, _defs in self.ext_definitions.items():
            for key, val in _defs.get("definitions", {}).items():
                _current = ext_counts.get(key, 0)
                _current += len(val)
                ext_counts[key] = _current
        root_counts = {}
        for key, val in self.root_definitions.get("definitions", {}).items():
            _current = root_counts.get(key, 0)
            _current += len(val)
            root_counts[key] = _current
        return dep_num, ext_counts, root_counts

    def setup_tmp_dir(self):
        if self.tmp_install_dir is None or not os.path.exists(self.tmp_install_dir.name):
            self.tmp_install_dir = tempfile.TemporaryDirectory()

    def clean_tmp_dir(self):
        if self.tmp_install_dir is not None and os.path.exists(self.tmp_install_dir.name):
            self.tmp_install_dir.cleanup()
            self.tmp_install_dir = None

    def create_load_file(self, target_type, target_name, target_path):

        loader_version = get_loader_version()

        if not os.path.exists(target_path):
            raise ValueError("No such file or directory: {}".format(target_path))
        if not self.silent:
            logging.debug("target_name", target_name)
            logging.debug("target_type", target_type)
            logging.debug("path", target_path)
            logging.debug("loader_version", loader_version)
        ld = Load(
            target_name=target_name,
            target_type=target_type,
            path=target_path,
            loader_version=loader_version,
        )
        load_object(ld)
        return ld

    def create_index_data(self, is_ext, ext_type, target_path_list):

        list = []
        if is_ext:
            for target_path in target_path_list:
                ext_name = get_target_name(ext_type, target_path)
                list.append(
                    {
                        "name": ext_name,
                        "type": ext_type,
                    }
                )
        else:
            list = [{"name": "", "type": ""}]
        return {
            "dependencies": list,
            "path_mappings": self.__path_mappings,
        }

    def load_ext_definitions_from_findings(self, type, name, version, hash):
        loaded, definitions, mappings = self.fm_db_client.load_definitions_from_findings(type, name, version, hash)
        if loaded:
            key = "{}-{}".format(type, name)
            self.ext_definitions[key] = {
                "definitions": definitions,
                "mappings": mappings,
            }
        return loaded

    def load_definition_ext(self, target_type, target_name, target_path):
        ld = self.create_load_file(target_type, target_name, target_path)
        use_cache = True
        output_dir = self.get_definition_path(ld.target_type, ld.target_name)
        if use_cache and os.path.exists(os.path.join(output_dir, "mappings.json")):
            if not self.silent:
                logging.debug("use cache from {}".format(output_dir))
            definitions, mappings = Parser.restore_definition_objects(output_dir)
        else:
            definitions, mappings = self._parser.run(load_data=ld)
            if self.do_save:
                if output_dir == "":
                    raise ValueError("Invalid output_dir")
                if not os.path.exists(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                Parser.dump_definition_objects(output_dir, definitions, mappings)

        key = "{}-{}".format(target_type, target_name)
        self.ext_definitions[key] = {
            "definitions": definitions,
            "mappings": mappings,
        }

    def load_definitions_from_findings(self, type, name, version, hash):
        loaded, definitions, mappings = self.fm_db_client.load_definitions_from_findings(type, name, version, hash)
        definitions_dict = {}
        if loaded:
            definitions_dict = {
                "definitions": definitions,
                "mappings": mappings,
            }
        return loaded, definitions_dict

    def load_definitions_root(self):

        output_dir = self.__path_mappings["root_definitions"]
        root_load = self._set_load_root()

        p = Parser(do_save=self.do_save)

        definitions, mappings = p.run(load_data=root_load)
        if self.do_save:
            if output_dir == "":
                raise ValueError("Invalid output_dir")
            if not os.path.exists(output_dir):
                os.makedirs(output_dir, exist_ok=True)
            Parser.dump_definition_objects(output_dir, definitions, mappings)

        self.root_definitions = {
            "definitions": definitions,
            "mappings": mappings,
        }

    def move_index(self, path1, path2, params):
        with open(path1, "r") as f1:
            js1 = json.load(f1)
            js2 = copy.deepcopy(js1)
            if any(params):
                for p in params:
                    js2[p] = params[p]
            with open(path2, "w") as f2:
                json.dump(js2, f2)

    def move_load_file(self, path1, src1, path2, src2):
        if os.path.exists(path2) and os.path.isdir(path2):
            raise ValueError("{} is not file".format(path2))

        js2 = None
        p1 = None
        p2 = None
        with open(path1, "r") as f1:
            js1 = json.load(f1)
            js2 = copy.deepcopy(js1)
            p1 = js1.get("path", "")
            p2 = p1.replace(src1, src2, 1)
            js2["path"] = p2

        if src1 != src2:

            if os.path.exists(p2):
                if os.path.isfile(p2):
                    raise ValueError("{} is not directory".format(p2))
            else:
                pass
                # os.makedirs(p2)

            def copytree(src, dst):
                if src == "" or not os.path.exists(src) or not os.path.isdir(src):
                    raise ValueError("src {} is not directory".format(src))
                if dst == "" or ".." in dst:
                    raise ValueError("dst {} is invalid".format(dst))
                os.system("cp -r {}/ {}/".format(src, dst))

            # use cp instead of shutil.copytree to avoid symlink reference loop
            copytree(p1, p2)

        with open(path2, "w") as f2:
            json.dump(js2, f2)

    def move_src(self, src, dst):
        if src == "" or not os.path.exists(src) or not os.path.isdir(src):
            raise ValueError("src {} is not directory".format(src))
        if dst == "" or ".." in dst:
            raise ValueError("dst {} is invalid".format(dst))
        os.system("cp -r {}/ {}/".format(src, dst))
        return

    def move_definitions(self, dir1, src1, dir2, src2):

        if not os.path.exists(dir2):
            pass
            # os.makedirs(dir2)
        if not os.path.isdir(dir2):
            raise ValueError("{} is not directory".format(dir2))

        if not os.path.exists(dir1) or not os.path.isdir(dir1):
            raise ValueError("{} is invalid definition directory".format(dir1))

        js2 = None
        map1 = os.path.join(dir1, "mappings.json")
        with open(map1, "r") as f1:
            js1 = json.load(f1)
            js2 = copy.deepcopy(js1)
            p1 = js1.get("path", "")
            p2 = p1.replace(src1, src2, 1)
            js2["path"] = p2

        if os.path.exists(dir2):
            shutil.rmtree(dir2)
        shutil.copytree(dir1, dir2, dirs_exist_ok=True)
        map2 = os.path.join(dir2, "mappings.json")
        with open(map2, "w") as f2:
            json.dump(js2, f2)

    def register_findings_to_fm(self):
        self.fm_db_client.register(self.findings)

    def save_findings(self, out_dir: str):
        self.fm_db_client.save_findings(self.findings, out_dir)


def tree(root_definitions, ext_definitions):
    tl = TreeLoader(root_definitions, ext_definitions)
    trees, additional = tl.run()
    if trees is None:
        raise ValueError("failed to get trees")
    # if node_objects is None:
    #     raise ValueError("failed to get node_objects")
    return trees, additional


def resolve(trees, additional):
    taskcalls_in_trees = []
    for tree in trees:
        if not isinstance(tree, ObjectList):
            continue
        if len(tree.items) == 0:
            continue
        root_key = tree.items[0].spec.key
        taskcalls = resolve_variables(tree, additional)
        d = TaskCallsInTree(
            root_key=root_key,
            taskcalls=taskcalls,
        )
        taskcalls_in_trees.append(d)
    return taskcalls_in_trees


if __name__ == "__main__":
    __target_type = sys.argv[1]
    __target_name = sys.argv[2]
    __dependency_dir = ""
    if len(sys.argv) >= 4:
        __dependency_dir = sys.argv[3]
    c = ARIScanner(
        type=__target_type,
        name=__target_name,
        root_dir=config.data_dir,
        dependency_dir=__dependency_dir,
    )
    c.load()


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
