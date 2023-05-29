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
import json
import yaml
import tempfile
import jsonpickle
import datetime
from dataclasses import dataclass, field

from .models import (
    Object,
    Load,
    LoadType,
    ObjectList,
    TaskCall,
    TaskCallsInTree,
    AnsibleRunContext,
    ARIResult,
)
from .loader import (
    get_loader_version,
)
from .parser import Parser
from .model_loader import load_object
from .tree import TreeLoader
from .annotators.variable_resolver import resolve_variables
from .analyzer import analyze
from .risk_detector import detect
from .dependency_dir_preparator import (
    DependencyDirPreparator,
)
from .findings import Findings
from .risk_assessment_model import RAMClient
import ansible_risk_insight.logger as logger
from .utils import (
    is_url,
    is_local_path,
    escape_url,
    escape_local_path,
    summarize_findings,
    summarize_findings_data,
    split_target_playbook_fullpath,
    split_target_taskfile_fullpath,
    equal,
)


default_config_path = os.path.expanduser("~/.ari/config")
default_data_dir = os.path.join("/tmp", "ari-data")
default_rules_dir = os.path.join(os.path.dirname(__file__), "rules")
default_log_level = "info"
default_rules = []
default_disable_default_rules = False
default_logger_key = "ari"


@dataclass
class Config:
    path: str = ""

    data_dir: str = ""
    rules_dir: str = ""
    logger_key: str = ""
    log_level: str = ""
    rules: list = field(default_factory=list)
    disable_default_rules: bool = False

    _data: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.path:
            self.path = default_config_path
        config_data = {}
        if os.path.exists(self.path):
            with open(self.path, "r") as file:
                try:
                    config_data = yaml.safe_load(file)
                except Exception as e:
                    raise ValueError(f"failed to load the config file: {e}")
        self._data = config_data

        if not self.data_dir:
            self.data_dir = self._get_single_config("ARI_DATA_DIR", "data_dir", default_data_dir)
        if not self.disable_default_rules:
            self.disable_default_rules = self._get_single_config("ARI_DISABLE_DEFAULT_RULES", "disable_default_rules", default_disable_default_rules)
        if not self.rules_dir:
            if self.disable_default_rules:
                self.rules_dir = self._get_single_config("ARI_RULES_DIR", "rules_dir", "")
            else:
                self.rules_dir = self._get_single_config("ARI_RULES_DIR", "rules_dir", default_rules_dir)
        # automatically add the default rules dir unless it is disabled
        if not self.rules_dir.endswith(default_rules_dir) and not self.disable_default_rules:
            self.rules_dir += ":" + default_rules_dir
        if not self.logger_key:
            self.logger_key = self._get_single_config("ARI_LOGGER_KEY", "logger_key", default_logger_key)
        if not self.log_level:
            self.log_level = self._get_single_config("ARI_LOG_LEVEL", "log_level", default_log_level)
        if not self.rules:
            self.rules = self._get_single_config("ARI_RULES", "rules", default_rules, "list", ",")

    def _get_single_config(self, env_key: str = "", yaml_key: str = "", __default: any = None, __type=None, separator=""):
        if env_key in os.environ:
            _from_env = os.environ.get(env_key, None)
            if _from_env and __type:
                if __type == "list":
                    _from_env = _from_env.split(separator)
            return _from_env
        elif yaml_key in self._data:
            _from_file = self._data.get(yaml_key, None)
            return _from_file
        else:
            return __default


collection_manifest_json = "MANIFEST.json"
role_meta_main_yml = "meta/main.yml"
role_meta_main_yaml = "meta/main.yaml"


supported_target_types = [
    LoadType.PROJECT,
    LoadType.COLLECTION,
    LoadType.ROLE,
    LoadType.PLAYBOOK,
]

config = Config()

logger.set_logger_channel(config.logger_key)
logger.set_log_level(config.log_level)


@dataclass
class SingleScan(object):
    type: str = ""
    name: str = ""
    collection_name: str = ""
    role_name: str = ""
    target_playbook_name: str = None
    playbook_yaml: str = ""
    playbook_only: bool = False
    target_taskfile_name: str = None
    taskfile_yaml: str = ""
    taskfile_only: bool = False

    skip_playbook_format_error: bool = (True,)
    skip_task_format_error: bool = (True,)

    install_log: str = ""
    tmp_install_dir: tempfile.TemporaryDirectory = None

    index: dict = field(default_factory=dict)

    root_definitions: dict = field(default_factory=dict)
    ext_definitions: dict = field(default_factory=dict)

    target_object: Object = field(default_factory=Object)

    trees: list = field(default_factory=list)
    # for inventory object
    additional: ObjectList = field(default_factory=ObjectList)

    taskcalls_in_trees: list = field(default_factory=list)
    contexts: list = field(default_factory=list)

    data_report: dict = field(default_factory=dict)

    __path_mappings: dict = field(default_factory=dict)

    install_dependencies: bool = False

    dependency_dir: str = ""
    target_path: str = ""
    loaded_dependency_dirs: list = field(default_factory=list)
    use_src_cache: bool = True

    prm: dict = field(default_factory=dict)

    download_url: str = ""
    version: str = ""
    hash: str = ""

    source_repository: str = ""
    out_dir: str = ""

    include_test_contents: bool = False
    load_all_taskfiles: bool = False

    extra_requirements: list = field(default_factory=list)
    resolve_failures: dict = field(default_factory=dict)

    findings: Findings = None
    result: ARIResult = None

    # the following are set by ARIScanner
    root_dir: str = ""
    rules_dir: str = ""
    rules: list = field(default_factory=list)
    rules_cache: list = field(default_factory=list)
    persist_dependency_cache: bool = False
    spec_mutations_from_previous_scan: dict = field(default_factory=dict)
    spec_mutations: dict = field(default_factory=dict)
    use_ansible_doc: bool = True
    do_save: bool = False
    silent: bool = False
    _parser: Parser = None

    def __post_init__(self):
        if self.type == LoadType.COLLECTION or self.type == LoadType.ROLE:
            type_root = self.type + "s"
            target_name = self.name
            if is_local_path(target_name):
                target_name = escape_local_path(target_name)
            self.__path_mappings = {
                "src": os.path.join(self.root_dir, type_root, "src"),
                "root_definitions": os.path.join(
                    self.root_dir,
                    type_root,
                    "root",
                    "definitions",
                    type_root,
                    target_name,
                ),
                "ext_definitions": {
                    LoadType.ROLE: os.path.join(self.root_dir, "roles", "definitions"),
                    LoadType.COLLECTION: os.path.join(self.root_dir, "collections", "definitions"),
                },
                "index": os.path.join(
                    self.root_dir,
                    type_root,
                    "{}-{}-index-ext.json".format(self.type, target_name),
                ),
                "install_log": os.path.join(
                    self.root_dir,
                    type_root,
                    "{}-{}-install.log".format(self.type, target_name),
                ),
            }

        elif self.type == LoadType.PROJECT or self.type == LoadType.PLAYBOOK or self.type == LoadType.TASKFILE:
            type_root = self.type + "s"
            proj_name = escape_url(self.name)
            if self.type == LoadType.PLAYBOOK:
                if self.playbook_yaml:
                    self.target_playbook_name = self.name
                else:
                    _, self.target_playbook_name = split_target_playbook_fullpath(self.name)
            elif self.type == LoadType.TASKFILE:
                if self.taskfile_yaml:
                    self.target_taskfile_name = self.name
                else:
                    _, self.target_taskfile_name = split_target_taskfile_fullpath(self.name)
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

        if self.playbook_yaml:
            self.playbook_only = True
            if not self.name:
                self.name = "__in_memory__"
                self.target_playbook_name = self.name

        if self.taskfile_yaml:
            self.taskfile_only = True
            if not self.name:
                self.name = "__in_memory__"
                self.target_taskfile_name = self.name

    def make_target_path(self, typ, target_name, dep_dir=""):
        target_path = ""

        if dep_dir:
            parts = target_name.split(".")
            if len(parts) == 1:
                parts.append("")
            dep_dir_target_path_candidates = [
                os.path.join(dep_dir, target_name),
                os.path.join(dep_dir, parts[0], parts[1]),
                os.path.join(dep_dir, "ansible_collections", parts[0], parts[1]),
            ]
            for cand_path in dep_dir_target_path_candidates:
                if os.path.exists(cand_path):
                    target_path = cand_path
                    break
        if target_path != "":
            return target_path

        if typ == LoadType.COLLECTION:
            parts = target_name.split(".")
            if is_local_path(target_name):
                target_path = target_name
            else:
                target_path = os.path.join(self.root_dir, typ + "s", "src", "ansible_collections", parts[0], parts[1])
        elif typ == LoadType.ROLE:
            if is_local_path(target_name):
                target_path = target_name
            else:
                target_path = os.path.join(self.root_dir, typ + "s", "src", target_name)
        elif typ == LoadType.PROJECT:
            if is_url(target_name):
                target_path = os.path.join(self.get_src_root(), escape_url(target_name))
            else:
                target_path = target_name
        elif typ == LoadType.PLAYBOOK:
            if is_url(target_name):
                target_path = os.path.join(self.get_src_root(), escape_url(target_name))
            else:
                target_path = target_name
        elif typ == LoadType.TASKFILE:
            if is_url(target_name):
                target_path = os.path.join(self.get_src_root(), escape_url(target_name))
            else:
                target_path = target_name
        return target_path

    def get_src_root(self):
        return self.__path_mappings["src"]

    def is_src_installed(self):
        index_location = self.__path_mappings["index"]
        return os.path.exists(index_location)

    def _prepare_dependencies(self, root_install=True):
        # Install the target if needed
        target_path = self.make_target_path(self.type, self.name)

        # Dependency Dir Preparator
        ddp = DependencyDirPreparator(
            root_dir=self.root_dir,
            source_repository=self.source_repository,
            target_type=self.type,
            target_name=self.name,
            target_version=self.version,
            target_path=target_path,
            target_dependency_dir=self.dependency_dir,
            target_path_mappings=self.__path_mappings,
            do_save=self.do_save,
            silent=self.silent,
            tmp_install_dir=self.tmp_install_dir,
            periodical_cleanup=self.persist_dependency_cache,
        )
        dep_dirs = ddp.prepare_dir(
            root_install=root_install,
            is_src_installed=self.is_src_installed(),
            cache_enabled=self.use_src_cache,
            cache_dir=os.path.join(self.root_dir, "archives"),
        )

        self.target_path = target_path
        self.version = ddp.metadata.version
        self.hash = ddp.metadata.hash
        self.download_url = ddp.metadata.download_url
        self.loaded_dependency_dirs = dep_dirs

        return target_path, dep_dirs

    def create_load_file(self, target_type, target_name, target_path):

        loader_version = get_loader_version()

        if not os.path.exists(target_path) and not self.playbook_yaml and not self.taskfile_yaml:
            raise ValueError("No such file or directory: {}".format(target_path))
        if not self.silent:
            logger.debug(f"target_name: {target_name}")
            logger.debug(f"target_type: {target_type}")
            logger.debug(f"path: {target_path}")
            logger.debug(f"loader_version: {loader_version}")
        ld = Load(
            target_name=target_name,
            target_type=target_type,
            path=target_path,
            loader_version=loader_version,
            playbook_yaml=self.playbook_yaml,
            playbook_only=self.playbook_only,
            taskfile_yaml=self.taskfile_yaml,
            taskfile_only=self.taskfile_only,
            include_test_contents=self.include_test_contents,
        )
        load_object(ld)
        return ld

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

    def load_definition_ext(self, target_type, target_name, target_path):
        ld = self.create_load_file(target_type, target_name, target_path)
        use_cache = True
        output_dir = self.get_definition_path(ld.target_type, ld.target_name)
        if use_cache and os.path.exists(os.path.join(output_dir, "mappings.json")):
            if not self.silent:
                logger.debug("use cache from {}".format(output_dir))
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
        return

    def _set_load_root(self, target_path=""):
        root_load_data = None
        if self.type in [LoadType.ROLE, LoadType.COLLECTION]:
            ext_type = self.type
            ext_name = self.name
            if target_path == "":
                target_path = self.get_source_path(ext_type, ext_name)
            root_load_data = self.create_load_file(ext_type, ext_name, target_path)
        elif self.type in [LoadType.PROJECT, LoadType.PLAYBOOK, LoadType.TASKFILE]:
            src_root = self.get_src_root()
            if target_path == "":
                target_path = os.path.join(src_root, escape_url(self.name))
            root_load_data = self.create_load_file(self.type, self.name, target_path)
        return root_load_data

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

    def load_definitions_root(self, target_path=""):

        output_dir = self.__path_mappings["root_definitions"]
        root_load = self._set_load_root(target_path=target_path)

        definitions, mappings = self._parser.run(load_data=root_load, collection_name_of_project=self.collection_name)
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

    def apply_spec_mutations(self):
        if not self.spec_mutations_from_previous_scan:
            return
        # overwrite the loaded object with the mutated object in spec mutations
        for type_name in self.root_definitions["definitions"]:
            obj_list = self.root_definitions["definitions"][type_name]
            for i, obj in enumerate(obj_list):
                key = obj.key
                if key in self.spec_mutations_from_previous_scan:
                    mutated_spec = self.spec_mutations_from_previous_scan[key].object
                    self.root_definitions["definitions"][type_name][i] = mutated_spec
        return

    def set_target_object(self):
        type_name = self.type + "s"
        obj_list = self.root_definitions.get("definitions", {}).get(type_name, [])
        if len(obj_list) == 0:
            return
        elif len(obj_list) == 1:
            self.target_object = obj_list[0]
        else:
            # only for playbook / taskfile not in `--xxxx-only` mode
            for obj in obj_list:
                obj_path = getattr(obj, "defined_in")
                if self.name in obj_path:
                    self.target_object = obj
                    break
        return

    def construct_trees(self, ram_client=None):
        trees, additional, extra_requirements, resolve_failures = tree(
            self.root_definitions,
            self.ext_definitions,
            ram_client,
            self.target_playbook_name,
            self.target_taskfile_name,
            self.load_all_taskfiles,
        )

        # set annotation for spec mutations
        if self.spec_mutations_from_previous_scan:
            spec_mutations = self.spec_mutations_from_previous_scan
            for _tree in trees:
                for callobj in _tree.items:
                    if not isinstance(callobj, TaskCall):
                        continue
                    obj_key = callobj.spec.key
                    if obj_key in spec_mutations:
                        m = spec_mutations[obj_key]
                        rule_id = m.rule.rule_id
                        value = {
                            "rule_id": rule_id,
                            "changes": m.changes,
                        }
                        callobj.set_annotation(key="spec.mutations", value=value, rule_id=rule_id)

        self.trees = trees
        self.additional = additional
        self.extra_requirements = extra_requirements
        self.resolve_failures = resolve_failures

        if self.do_save:
            root_def_dir = self.__path_mappings["root_definitions"]
            tree_rel_file = os.path.join(root_def_dir, "tree.json")
            if tree_rel_file != "":
                lines = []
                for t_obj_list in self.trees:
                    lines.append(t_obj_list.to_one_line_json())
                open(tree_rel_file, "w").write("\n".join(lines))
                if not self.silent:
                    logger.info("  tree file saved")
        return

    def resolve_variables(self, ram_client=None):
        taskcalls_in_trees = resolve(self.trees, self.additional)
        self.taskcalls_in_trees = taskcalls_in_trees

        for i, tree in enumerate(self.trees):
            last_item = i + 1 == len(self.trees)
            ctx = AnsibleRunContext.from_tree(tree=tree, parent=self.target_object, last_item=last_item, ram_client=ram_client)
            self.contexts.append(ctx)

        if self.do_save:
            root_def_dir = self.__path_mappings["root_definitions"]
            tasks_in_t_path = os.path.join(root_def_dir, "tasks_in_trees.json")
            tasks_in_t_lines = []
            for d in taskcalls_in_trees:
                line = jsonpickle.encode(d, make_refs=False)
                tasks_in_t_lines.append(line)

            open(tasks_in_t_path, "w").write("\n".join(tasks_in_t_lines))
        return

    def annotate(self):
        contexts = analyze(self.contexts)
        self.contexts = contexts

        if self.do_save:
            root_def_dir = self.__path_mappings["root_definitions"]
            contexts_a_path = os.path.join(root_def_dir, "contexts_with_analysis.json")
            conetxts_a_lines = []
            for d in contexts:
                line = jsonpickle.encode(d, make_refs=False)
                conetxts_a_lines.append(line)

            open(contexts_a_path, "w").write("\n".join(conetxts_a_lines))

        return

    def apply_rules(self):
        target_name = self.name
        if self.collection_name:
            target_name = self.collection_name
        if self.role_name:
            target_name = self.role_name
        data_report, rules_cache = detect(self.contexts, rules_dir=self.rules_dir, rules=self.rules, rules_cache=self.rules_cache)
        self.rules_cache = rules_cache
        spec_mutations = data_report.get("spec_mutations", {})
        if spec_mutations:
            self.spec_mutations = spec_mutations
        metadata = {
            "type": self.type,
            "name": target_name,
            "version": self.version,
            "source": self.source_repository,
            "download_url": self.download_url,
            "hash": self.hash,
        }
        dependencies = self.loaded_dependency_dirs

        summary_txt = summarize_findings_data(
            metadata,
            dependencies,
            data_report,
            self.resolve_failures,
            self.extra_requirements,
        )
        self.findings = Findings(
            metadata=metadata,
            dependencies=dependencies,
            root_definitions=self.root_definitions,
            ext_definitions=self.ext_definitions,
            extra_requirements=self.extra_requirements,
            resolve_failures=self.resolve_failures,
            prm=self.prm,
            report=data_report,
            summary_txt=summary_txt,
            scan_time=datetime.datetime.utcnow().isoformat(),
        )
        self.result = data_report.get("ari_result", None)
        return

    def add_time_records(self, time_records: dict):
        if self.findings:
            self.findings.metadata["time_records"] = time_records
        return

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

    def set_metadata(self, metadata: dict, dependencies: dict):
        self.target_path = self.make_target_path(self.type, self.name)
        self.version = metadata.get("version", "")
        self.hash = metadata.get("hash", "")
        self.download_url = metadata.get("download_url", "")
        self.loaded_dependency_dirs = dependencies

    def set_metadata_findings(self):
        target_name = self.name
        if self.collection_name:
            target_name = self.collection_name
        if self.role_name:
            target_name = self.role_name
        metadata = {
            "type": self.type,
            "name": target_name,
            "version": self.version,
            "source": self.source_repository,
            "download_url": self.download_url,
            "hash": self.hash,
        }
        dependencies = self.loaded_dependency_dirs
        self.findings = Findings(
            metadata=metadata,
            dependencies=dependencies,
        )

    def load_index(self):
        index_location = self.__path_mappings["index"]
        with open(index_location, "r") as f:
            self.index = json.load(f)


@dataclass
class ARIScanner(object):
    config: Config = None

    root_dir: str = ""
    rules_dir: str = ""
    rules: list = field(default_factory=list)
    rules_cache: list = field(default_factory=list)

    ram_client: RAMClient = None
    read_ram: bool = True
    read_ram_for_dependency: bool = True
    write_ram: bool = False

    persist_dependency_cache: bool = False

    skip_playbook_format_error: bool = (True,)
    skip_task_format_error: bool = (True,)

    use_ansible_doc: bool = True

    do_save: bool = False
    _parser: Parser = None

    show_all: bool = False
    pretty: bool = False
    silent: bool = False
    output_format: str = ""

    _current: SingleScan = None

    def __post_init__(self):
        if not self.config:
            self.config = config

        if not self.root_dir:
            self.root_dir = self.config.data_dir
        if not self.rules_dir:
            self.rules_dir = self.config.rules_dir
        if not self.rules:
            self.rules = self.config.rules
        if not self.ram_client:
            self.ram_client = RAMClient(root_dir=self.root_dir)
        self._parser = Parser(
            do_save=self.do_save,
            use_ansible_doc=self.use_ansible_doc,
            skip_playbook_format_error=self.skip_playbook_format_error,
            skip_task_format_error=self.skip_task_format_error,
        )

        if not self.silent:
            logger.debug(f"config: {self.config}")

    def evaluate(
        self,
        type: str,
        name: str = "",
        path: str = "",
        collection_name: str = "",
        role_name: str = "",
        install_dependencies: bool = True,
        version: str = "",
        hash: str = "",
        target_path: str = "",
        dependency_dir: str = "",
        download_only: bool = False,
        load_only: bool = False,
        skip_dependency: bool = False,
        use_src_cache: bool = False,
        source_repository: str = "",
        playbook_yaml: str = "",
        playbook_only: bool = False,
        taskfile_yaml: str = "",
        taskfile_only: bool = False,
        raw_yaml: str = "",
        include_test_contents: bool = False,
        load_all_taskfiles: bool = False,
        objects: bool = False,
        out_dir: str = "",
        spec_mutations_from_previous_scan: dict = None,
    ):
        time_records = {}
        self.record_begin(time_records, "scandata_init")

        if not name and path:
            name = path

        if raw_yaml:
            if type == LoadType.PLAYBOOK:
                playbook_yaml = raw_yaml
            elif type == LoadType.TASKFILE:
                taskfile_yaml = raw_yaml

        if is_local_path(name):
            name = os.path.abspath(name)

        scandata = SingleScan(
            type=type,
            name=name,
            collection_name=collection_name,
            role_name=role_name,
            install_dependencies=install_dependencies,
            version=version,
            hash=hash,
            target_path=target_path,
            skip_playbook_format_error=self.skip_playbook_format_error,
            skip_task_format_error=self.skip_task_format_error,
            dependency_dir=dependency_dir,
            use_src_cache=use_src_cache,
            source_repository=source_repository,
            playbook_yaml=playbook_yaml,
            playbook_only=playbook_only,
            taskfile_yaml=taskfile_yaml,
            taskfile_only=taskfile_only,
            include_test_contents=include_test_contents,
            load_all_taskfiles=load_all_taskfiles,
            out_dir=out_dir,
            root_dir=self.root_dir,
            rules_dir=self.rules_dir,
            rules=self.rules,
            rules_cache=self.rules_cache,
            persist_dependency_cache=self.persist_dependency_cache,
            spec_mutations_from_previous_scan=spec_mutations_from_previous_scan,
            use_ansible_doc=self.use_ansible_doc,
            do_save=self.do_save,
            silent=self.silent,
            _parser=self._parser,
        )
        self._current = scandata
        self.record_end(time_records, "scandata_init")

        self.record_begin(time_records, "metadata_load")
        metdata_loaded = False
        if self.read_ram and scandata.type not in [LoadType.PLAYBOOK, LoadType.TASKFILE, LoadType.PROJECT]:
            loaded, metadata, dependencies = self.load_metadata_from_ram(scandata.type, scandata.name, scandata.version)
            logger.debug(f"metadata loaded: {loaded}")
            if loaded:
                scandata.set_metadata(metadata, dependencies)
                metdata_loaded = True
                if not self.silent:
                    logger.debug(f'Use metadata for "{scandata.name}" in RAM DB')

        if scandata.install_dependencies and not metdata_loaded:
            logger.debug(f"start preparing {scandata.type} {scandata.name}")
            scandata._prepare_dependencies()
            logger.debug(f"finished preparing {scandata.type} {scandata.name}")

        if download_only:
            scandata.set_metadata_findings()
            self.register_findings_to_ram(scandata.findings)
            return None
        self.record_end(time_records, "metadata_load")

        if not skip_dependency:
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
                    for d in scandata.loaded_dependency_dirs
                ]
            )
            ext_count = len(ext_list)

            # Start ARI Scanner main flow
            self.record_begin(time_records, "dependency_load")
            for i, (ext_type, ext_name, ext_ver, ext_hash, ext_path) in enumerate(ext_list):
                if not self.silent:
                    if i == 0:
                        logger.info("start loading {} {}(s)".format(ext_count, ext_type))
                    logger.info("[{}/{}] {} {}".format(i + 1, ext_count, ext_type, ext_name))

                # avoid infinite loop
                is_root = False
                if scandata.type == ext_type and scandata.name == ext_name:
                    is_root = True

                if not is_root:
                    key = "{}-{}".format(ext_type, ext_name)
                    read_ram_for_dependency = self.read_ram or self.read_ram_for_dependency

                    dep_loaded = False
                    if read_ram_for_dependency:
                        # searching findings from ARI RAM and use them if found
                        dep_loaded, ext_defs = self.load_definitions_from_ram(ext_type, ext_name, ext_ver, ext_hash)
                        if dep_loaded:
                            scandata.ext_definitions[key] = ext_defs
                            if not self.silent:
                                logger.debug(f'Use spec data for "{ext_name}" in RAM DB')

                    if not dep_loaded:
                        # scan dependencies and save findings to ARI RAM
                        dep_scanner = ARIScanner(
                            root_dir=self.root_dir,
                            rules_dir="",
                            rules=[],
                            ram_client=self.ram_client,
                            read_ram=read_ram_for_dependency,
                            read_ram_for_dependency=self.read_ram_for_dependency,
                            write_ram=self.write_ram,
                            use_ansible_doc=self.use_ansible_doc,
                            do_save=self.do_save,
                            silent=True,
                        )
                        ext_target_path = os.path.join(self.root_dir, ext_path)
                        # use prepared dep dirs
                        dep_scanner.evaluate(
                            type=ext_type,
                            name=ext_name,
                            version=ext_ver,
                            hash=ext_hash,
                            target_path=ext_target_path,
                            dependency_dir=scandata.dependency_dir,
                            install_dependencies=False,
                            skip_dependency=True,
                            source_repository=scandata.source_repository,
                            include_test_contents=include_test_contents,
                            load_all_taskfiles=load_all_taskfiles,
                            load_only=True,
                        )
                        dep_scandata = dep_scanner.get_last_scandata()
                        scandata.ext_definitions[key] = dep_scandata.root_definitions
                        dep_loaded = True

            self.record_end(time_records, "dependency_load")

            if not self.silent:
                logger.debug("load_definition_ext() done")

        # PRM Finder
        self.record_begin(time_records, "prm_load")
        # playbooks, roles, modules = find_playbook_role_module(scandata.target_path, self.use_ansible_doc)
        # scandata.prm["playbooks"] = playbooks
        # scandata.prm["roles"] = roles
        # scandata.prm["modules"] = modules
        self.record_end(time_records, "prm_load")

        loaded = False
        self.record_begin(time_records, "target_load")
        if self.read_ram and scandata.type not in [LoadType.PLAYBOOK, LoadType.TASKFILE, LoadType.PROJECT]:
            loaded, root_defs = self.load_definitions_from_ram(scandata.type, scandata.name, scandata.version, scandata.hash, allow_unresolved=True)
            logger.debug(f"spec data loaded: {loaded}")
            if loaded:
                scandata.root_definitions = root_defs
                if not self.silent:
                    logger.info("Use spec data in RAM DB")
        self.record_end(time_records, "target_load")

        if not loaded:
            scandata.load_definitions_root(target_path=scandata.target_path)

        scandata.set_target_object()

        if not self.silent:
            logger.debug("load_definitions_root() done")
            playbooks_num = len(scandata.root_definitions["definitions"]["playbooks"])
            roles_num = len(scandata.root_definitions["definitions"]["roles"])
            taskfiles_num = len(scandata.root_definitions["definitions"]["taskfiles"])
            tasks_num = len(scandata.root_definitions["definitions"]["tasks"])
            modules_num = len(scandata.root_definitions["definitions"]["modules"])
            logger.debug(f"playbooks: {playbooks_num}, roles: {roles_num}, taskfiles: {taskfiles_num}, tasks: {tasks_num}, modules: {modules_num}")

        self.record_begin(time_records, "apply_spec_rules")
        scandata.apply_spec_mutations()
        self.record_end(time_records, "apply_spec_rules")
        if not self.silent:
            logger.debug("apply_spec_rules() done")

        # load_only is True when this scanner is scanning dependency
        # otherwise, move on tree construction / rule evaluation
        if load_only:
            return None

        _ram_client = None
        if self.read_ram:
            _ram_client = self.ram_client

        self.record_begin(time_records, "tree_construction")
        scandata.construct_trees(_ram_client)
        self.record_end(time_records, "tree_construction")
        if not self.silent:
            logger.debug("construct_trees() done")

        self.record_begin(time_records, "variable_resolution")
        scandata.resolve_variables(_ram_client)
        self.record_end(time_records, "variable_resolution")
        if not self.silent:
            logger.debug("resolve_variables() done")

        self.record_begin(time_records, "module_annotators")
        scandata.annotate()
        self.record_end(time_records, "module_annotators")
        if not self.silent:
            logger.debug("annotate() done")

        self.record_begin(time_records, "apply_rules")
        scandata.apply_rules()
        self.record_end(time_records, "apply_rules")
        if not self.silent:
            logger.debug("apply_rules() done")

        if scandata.rules_cache:
            self.rules_cache = scandata.rules_cache

        scandata.add_time_records(time_records=time_records)

        dep_num, ext_counts, root_counts = scandata.count_definitions()
        if not self.silent:
            print("# of dependencies:", dep_num)
            # print("ext definitions:", ext_counts)
            # print("root definitions:", root_counts)

        # save RAM data
        if self.write_ram and scandata.type not in [LoadType.PLAYBOOK, LoadType.TASKFILE, LoadType.PROJECT]:
            self.register_findings_to_ram(scandata.findings)
            self.register_indices_to_ram(scandata.findings, include_test_contents)

        if scandata.out_dir is not None and scandata.out_dir != "":
            self.save_rule_result(scandata.findings, scandata.out_dir)
            if not self.silent:
                print("The rule result is saved at {}".format(scandata.out_dir))

            if objects:
                self.save_definitions(scandata.root_definitions, scandata.out_dir)
                if not self.silent:
                    print("The objects is saved at {}".format(scandata.out_dir))

        if not self.silent:
            summary = summarize_findings(scandata.findings, self.show_all)
            print(summary)

        if self.pretty:
            data_str = ""
            data = json.loads(jsonpickle.encode(scandata.findings.simple(), make_refs=False))
            if self.output_format.lower() == "json":
                data_str = json.dumps(data, indent=2)
            elif self.output_format.lower() == "yaml":
                data_str = yaml.safe_dump(data)
            print(data_str)

        if scandata.spec_mutations:
            trigger_rescan = False
            _previous = spec_mutations_from_previous_scan
            if _previous and equal(scandata.spec_mutations, _previous):
                if not self.silent:
                    logger.warning("Spec mutation loop has been detected! " "Exitting the scan here but the result may be incomplete.")
            else:
                trigger_rescan = True

            if trigger_rescan:
                if not self.silent:
                    print("Spec mutations are found. Triggering ARI scan again...")
                return self.evaluate(
                    type=type,
                    name=name,
                    path=path,
                    collection_name=collection_name,
                    role_name=role_name,
                    install_dependencies=install_dependencies,
                    version=version,
                    hash=hash,
                    target_path=target_path,
                    dependency_dir=dependency_dir,
                    download_only=download_only,
                    load_only=load_only,
                    skip_dependency=skip_dependency,
                    use_src_cache=use_src_cache,
                    source_repository=source_repository,
                    playbook_yaml=playbook_yaml,
                    playbook_only=playbook_only,
                    taskfile_yaml=taskfile_yaml,
                    taskfile_only=taskfile_only,
                    include_test_contents=include_test_contents,
                    load_all_taskfiles=load_all_taskfiles,
                    objects=objects,
                    raw_yaml=raw_yaml,
                    out_dir=out_dir,
                    spec_mutations_from_previous_scan=scandata.spec_mutations,
                )

        return scandata.findings.report.get("ari_result", None)

    def load_metadata_from_ram(self, type, name, version):
        loaded, metadata, dependencies = self.ram_client.load_metadata_from_findings(type, name, version)
        return loaded, metadata, dependencies

    def load_definitions_from_ram(self, type, name, version, hash, allow_unresolved=False):
        loaded, definitions, mappings = self.ram_client.load_definitions_from_findings(type, name, version, hash, allow_unresolved)
        definitions_dict = {}
        if loaded:
            definitions_dict = {
                "definitions": definitions,
                "mappings": mappings,
            }
        return loaded, definitions_dict

    def register_findings_to_ram(self, findings: Findings):
        self.ram_client.register(findings)

    def register_indices_to_ram(self, findings: Findings, include_test_contents: bool = False):
        self.ram_client.register_indices_to_ram(findings, include_test_contents)

    def save_findings(self, findings: Findings, out_dir: str):
        self.ram_client.save_findings(findings, out_dir)

    def save_rule_result(self, findings: Findings, out_dir: str):
        if out_dir == "":
            raise ValueError("output dir must be a non-empty value")

        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        findings.save_rule_result(fpath=os.path.join(out_dir, "rule_result.json"))

    def save_definitions(self, definitions: dict, out_dir: str):
        if out_dir == "":
            raise ValueError("output dir must be a non-empty value")

        if not os.path.exists(out_dir):
            os.makedirs(out_dir, exist_ok=True)

        objects_json_str = jsonpickle.encode(definitions["definitions"], make_refs=False)
        fpath = os.path.join(out_dir, "objects.json")
        with open(fpath, "w") as file:
            file.write(objects_json_str)

    def get_last_scandata(self):
        return self._current

    def save_error(self, error: str, out_dir: str = ""):
        if out_dir == "":
            type = self._current.type
            name = self._current.name
            version = self._current.version
            hash = self._current.hash
            out_dir = self.ram_client.make_findings_dir_path(type, name, version, hash)
        self.ram_client.save_error(error, out_dir)

    def record_begin(self, time_records: dict, record_name: str):
        time_records[record_name] = {}
        time_records[record_name]["begin"] = datetime.datetime.utcnow().isoformat()

    def record_end(self, time_records: dict, record_name: str):
        end = datetime.datetime.utcnow()
        time_records[record_name]["end"] = end.isoformat()
        begin = datetime.datetime.fromisoformat(time_records[record_name]["begin"])
        elapsed = (end - begin).total_seconds()
        time_records[record_name]["elapsed"] = elapsed


def tree(root_definitions, ext_definitions, ram_client=None, target_playbook_path=None, target_taskfile_path=None, load_all_taskfiles=False):
    tl = TreeLoader(root_definitions, ext_definitions, ram_client, target_playbook_path, target_taskfile_path, load_all_taskfiles)
    trees, additional = tl.run()
    if trees is None:
        raise ValueError("failed to get trees")
    # if node_objects is None:
    #     raise ValueError("failed to get node_objects")
    return (
        trees,
        additional,
        tl.extra_requirements,
        tl.resolve_failures,
    )


def resolve(trees, additional):
    taskcalls_in_trees = []
    for i, tree in enumerate(trees):
        if not isinstance(tree, ObjectList):
            continue
        if len(tree.items) == 0:
            continue
        root_key = tree.items[0].spec.key
        logger.debug("[{}/{}] {}".format(i + 1, len(trees), root_key))
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
        root_dir=config.data_dir,
    )
    c.evaluate(
        type=__target_type,
        name=__target_name,
        dependency_dir=__dependency_dir,
    )
