import os
import sys
import copy
import shutil
import subprocess
import json
import yaml
import tempfile
import logging
from dataclasses import dataclass, field
from models import LoadType, Load, ObjectList
from loader import (
    detect_target_type,
    supported_target_types,
    get_loader_version,
    create_load_json_path,
    get_target_name,
)
from parser import Parser
from model_loader import load_object
from tree import TreeLoader, TreeNode
from variable_resolver import resolve_variables
from analyzer import analyze
from risk_detector import detect


class Config:
    data_dir: str = os.environ.get(
        "ARI_DATA_DIR", os.path.join(os.environ["HOME"], ".ari/data")
    )
    log_level: str = os.environ.get(
        "ARI_LOG_LEVEL", "info"
    ).lower()


log_level_map = {
    "error": logging.ERROR,
    "warning": logging.WARNING,
    "info": logging.INFO,
    "debug": logging.DEBUG,
}


config = Config()


logging.basicConfig()
logging.getLogger().setLevel(log_level_map[config.log_level])


class ContainerType:
    COLLECTION = "collection"
    ROLE = "role"
    PROJECT = "project"


@dataclass
class DataContainer(object):
    type: str = ""
    name: str = ""
    id: str = ""

    src: str = ""
    install_log: str = ""
    tmp_install_dir: tempfile.TemporaryDirectory = None

    index: dict = field(default_factory=dict)
    _root_load: Load = Load()
    _ext_load: list = field(default_factory=list)

    root_definitions: dict = field(default_factory=dict)
    ext_definitions: dict = field(default_factory=dict)

    trees: list = field(default_factory=list)
    node_objects: ObjectList = ObjectList()

    tasks_rv: list = field(default_factory=list)
    tasks_rva: list = field(default_factory=list)

    report_to_display: str = ""

    # TODO: remove attributes below once refactoring is done
    root_dir: str = ""
    path_mappings: dict = field(default_factory=dict)

    dependency_dir: str = ""
    do_save: bool = False
    _parser: Parser = None


    def __post_init__(self):
        type_root = self.type + "s"
        self.path_mappings = {
            "src": os.path.join(self.root_dir, type_root, "src"),
            "root_load": os.path.join(
                self.root_dir,
                type_root,
                "root",
                "{}-{}-load-root.json".format(self.type, self.name),
            ),
            "root_definitions": os.path.join(
                self.root_dir,
                type_root,
                "root",
                "definitions",
                type_root,
                self.name,
            ),
            "ext_load": os.path.join(
                self.root_dir,
                type_root,
                "ext",
                "load-{}-{}.json".format(self.type, self.name),
            ),
            "ext_definitions": {
                ContainerType.ROLE: os.path.join(self.root_dir, "roles", "definitions"),
                ContainerType.COLLECTION: os.path.join(self.root_dir, "collections", "definitions")
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

    def load(self):
        src_location = self.path_mappings.get("src", "")
        self.set_src(src_location)
        logging.debug("set_src() done")
        if self.isinstalled():
            self.load_index()
        else:
            try:
                self.setup_tmp_dir()
                self.install()
                logging.debug("install() done")
            finally:
                self.clean_tmp_dir()

        load_file_info_list = self.index.get("generated_load_files", [])
        ext_count = len(load_file_info_list)
        if ext_count == 0:
            logging.info("no target dirs found. exitting.")
            sys.exit()

        self._parser = Parser(do_save=self.do_save)
        for i, load_file_info in enumerate(load_file_info_list):
            ext_type = load_file_info.get("type", "")
            ext_name = load_file_info.get("name", "")
            ext_path = self.get_source_path(ext_type, ext_name)
            if i == 0:
                logging.info("start loading {} {}(s)".format(ext_count, ext_type))
            logging.info(
                "[{}/{}] {} {}".format(i + 1, ext_count, ext_type, ext_name)
            )
            self.load_definition_ext(ext_type, ext_name, ext_path)

        logging.debug("load_definition_ext() done")

        self.load_definitions_root()
        logging.debug("load_definitions_root() done")

        self.set_trees()
        logging.debug("set_trees() done")
        self.set_resolved()
        logging.debug("set_resolved() done")
        self.set_analyzed()
        logging.debug("set_analyzed() done")
        self.set_report()
        logging.debug("set_report() done")
        dep_num, ext_counts, root_counts = self.count_definitions()
        print("# of dependencies:", dep_num)
        print("ext definitions:", ext_counts)
        print("root definitions:", root_counts)

        print(self.report_to_display)
        return

    def set_src(self, src_location):
        self.src = src_location

    def get_src(self):
        return self.src

    def isinstalled(self):
        index_location = self.path_mappings.get("index", "")
        return os.path.exists(index_location)

    def load_index(self):
        index_location = self.path_mappings.get("index", "")
        with open(index_location, "r") as f:
            self.index = json.load(f)
        return os.path.exists(index_location)

    def install(self):
        tmpdir = self.tmp_install_dir.name
        tmp_install_log = os.path.join(tmpdir, "install.log")
        tmp_src_dir = os.path.join(tmpdir, "src")
        is_ext = True

        install_type = ""
        if self.type in [ContainerType.COLLECTION, ContainerType.ROLE]:
            install_type = "galaxy"
        elif self.type == ContainerType.PROJECT:
            install_type = "github"

        install_msg = ""
        dependency_dir = ""
        dst_src_dir = ""
        if install_type == "galaxy":
            # ansible-galaxy install
            print(
                "installing a {} <{}> from galaxy".format(
                    self.type, self.name
                )
            )
            install_msg = install_galaxy_target(
                self.name, self.type, tmp_src_dir
            )
            dependency_dir = tmp_src_dir
            dst_src_dir = self.src

        elif install_type == "github":
            # ansible-galaxy install
            print("cloning {} from github".format(self.name))
            install_msg = install_github_target(
                self.name, self.type, tmp_src_dir
            )
            if self.dependency_dir == "":
                raise ValueError(
                    "dependency dir is required for project type"
                )
            dependency_dir = self.dependency_dir
            dst_src_dir = os.path.join(self.src, escape_url(self.name))

        with open(tmp_install_log, "w") as f:
            f.write(install_msg)
            print(install_msg)
        self.install_log = install_msg

        print("crawl content")
        dep_type, target_path_list = detect_target_type(
            dependency_dir, is_ext
        )

        dst_dependency_dir = ""
        if install_type == "github":
            type_root = dep_type + "s"
            dst_dependency_dir = os.path.join(self.root_dir, type_root, "src")

        logging.info(
            'the detected target type: "{}", found targets: {}'.format(
                self.type, len(target_path_list)
            )
        )
        if self.type not in supported_target_types:
            logging.error("this target type is not supported")
            sys.exit(1)

        tmp_load_files_dir = os.path.join(tmpdir, "ext")
        collection_search_path = os.path.join(config.data_dir, "collections")
        index_data = self.create_index_data(
            is_ext,
            dep_type,
            target_path_list,
            dependency_dir,
            collection_search_path,
            tmp_load_files_dir,
        )
        if index_data.get("out_path", "") == "":
            raise ValueError("no out_path in index file")

        if not os.path.exists(dst_src_dir):
            os.makedirs(dst_src_dir)

        type_root = self.type + "s"
        dst_load_files_dir = os.path.join(self.root_dir, type_root, "ext")
        # if not os.path.exists(dst_load_files_dir):
        #     os.makedirs(dst_load_files_dir)

        print("moving index")
        index_data["in_path"] = dst_src_dir
        index_data["out_path"] = dst_load_files_dir
        self.index = index_data
        logging.debug("index: {}".format(json.dumps(self.index)))

        index_location = self.path_mappings.get("index", "")
        index_dir = os.path.dirname(os.path.abspath(index_location))
        if not os.path.exists(index_dir):
            os.makedirs(index_dir)
        with open(index_location, "w") as f:
            json.dump(self.index, f, indent=2)

        self.move_src(tmp_src_dir, dst_src_dir)
        if dst_dependency_dir != "":
            self.move_src(dependency_dir, dst_dependency_dir)
        return

    def get_index(self):
        return self.index

    def _get_target_list(self):
        load_file_info_list = self.index.get("generated_load_files", [])
        target_list = []
        for load_file_info in load_file_info_list:
            ext_type = load_file_info.get("type", "")
            ext_name = load_file_info.get("name", "")
            target_path = self.get_source_path(ext_type, ext_name)
            target_list.append((ext_type, ext_name, target_path))
        return target_list

    def get_definition_path(self, ext_type, ext_name):
        target_path = ""
        if ext_type == ContainerType.ROLE:
            target_path = os.path.join(
                self.path_mappings.get("ext_definitions",{}).get(ContainerType.ROLE, ""),
                ext_name
            )
        elif ext_type == ContainerType.COLLECTION:
            target_path = os.path.join(
                self.path_mappings.get("ext_definitions",{}).get(ContainerType.COLLECTION, ""),
                ext_name
            )
        else:
            raise ValueError("Invalid ext_type")
        return target_path

    def get_source_path(self, ext_type, ext_name):
        target_path = ""
        if ext_type == ContainerType.ROLE:
            target_path = os.path.join(
                self.root_dir, "roles", "src", ext_name
            )
        elif ext_type == ContainerType.COLLECTION:
            parts = ext_name.split(".")
            target_path = os.path.join(
                self.root_dir,
                "collections",
                "src",
                "ansible_collections",
                parts[0],
                parts[1],
            )
        else:
            raise ValueError("Invalid ext_type")
        return target_path


    def _set_load_root(self):
        root_load_data = None
        if self.type in [ContainerType.ROLE, ContainerType.COLLECTION]:
            ext_type = self.type
            ext_name = self.name
            target_path = self.get_source_path(ext_type, ext_name)
            root_load_data = self.create_load_file(ext_type, ext_name, target_path)
        elif self.type == ContainerType.PROJECT:
            dst_src_dir = os.path.join(self.src, escape_url(self.name))
            root_load_data = self.create_load_file(self.type, self.name, dst_src_dir)
        return root_load_data

    def get_definitions(self):
        return self.root_definitions, self.ext_definitions

    def set_trees(self):
        trees, node_objects = self.tree(
            self.root_definitions, self.ext_definitions, self.index
        )
        self.trees = trees
        self.node_objects = node_objects
        return

    def get_trees(self):
        return self.trees, self.node_objects

    def set_resolved(self):
        tasks_rv = self.resolve(self.trees, self.node_objects)
        self.tasks_rv = tasks_rv
        return

    def get_resolved(self):
        return self.get_tasks_rv()

    def get_tasks_rv(self):
        return self.tasks_rv

    def set_analyzed(self):
        tasks_rva = analyze(self.tasks_rv)
        self.tasks_rva = tasks_rva
        return

    def get_analyzed(self):
        return self.tasks_rva

    def set_report(self):
        coll_type = ContainerType.COLLECTION
        coll_name = self.name if self.type == coll_type else ""
        report_txt = detect(self.tasks_rva, collection_name=coll_name)
        self.report_to_display = report_txt
        return

    def get_report(self):
        return self.report_to_display

    def count_definitions(self):
        dep_num = len(self.ext_definitions)
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
        if self.tmp_install_dir is None or not os.path.exists(
            self.tmp_install_dir.name
        ):
            self.tmp_install_dir = tempfile.TemporaryDirectory()

    def clean_tmp_dir(self):
        if self.tmp_install_dir is not None and os.path.exists(
            self.tmp_install_dir.name
        ):
            self.tmp_install_dir.cleanup()
            self.tmp_install_dir = None

    def create_load_file(self, target_type, target_name, target_path):

        loader_version = get_loader_version()

        if not os.path.exists(target_path):
            raise ValueError(
                "No such file or directory: {}".format(target_path)
            )
        print("target_name", target_name)
        print("target_type", target_type)
        print("path", target_path)
        print("loader_version", loader_version)
        ld = Load(
            target_name=target_name,
            target_type=target_type,
            path=target_path,
            loader_version=loader_version,
        )
        load_object(ld)
        return ld


    def create_index_data(
        self,
        is_ext,
        dep_type,
        target_path_list,
        src_dir,
        collection_search_path,
        output_path,
    ):
        target_type = self.type
        index_data = {
            "in_path": src_dir,
            "out_path": output_path,
            "collection_path": collection_search_path,
            "mode": "ext" if is_ext else "root",
            "target_type": target_type,
            "generated_load_files": [],
            "dep_collection_load_files": [],
        }

        generated_load_files = []
        if is_ext:

            for target_path in target_path_list:
                dep_name = get_target_name(dep_type, target_path)
                load_json_path = create_load_json_path(
                    dep_type, dep_name, output_path
                )
                lf = load_json_path.replace(output_path, "")
                if lf.startswith("/"):
                    lf = lf[1:]
                generated_load_files.append(
                    {
                        "file": lf,
                        "name": dep_name,
                        "type": dep_type,
                    }
                )
        else:
            generated_load_files = [
                {"file": output_path, "name": "", "type": ""}
            ]
        index_data["generated_load_files"] = generated_load_files

        dep_collection_load_files = []
        if target_type == LoadType.ROLE_TYPE:
            dep_collection_load_files = (
                self.find_load_files_for_dependency_collections(
                    target_path_list, collection_search_path
                )
            )
            index_data[
                "dep_collection_load_files"
            ] = dep_collection_load_files

        return index_data

    def find_load_files_for_dependency_collections(
        self, role_path_list, collection_search_path
    ):
        dep_collections = []
        for role_path in role_path_list:
            _metadata_path_cand1 = os.path.join(role_path, "meta/main.yml")
            _metadata_path_cand2 = os.path.join(role_path, "meta/main.yaml")
            metadata_path = ""
            if os.path.exists(_metadata_path_cand1):
                metadata_path = _metadata_path_cand1
            elif os.path.exists(_metadata_path_cand2):
                metadata_path = _metadata_path_cand2
            if metadata_path == "":
                continue
            metadata = {}
            try:
                metadata = yaml.safe_load(open(metadata_path, "r"))
            except Exception:
                pass
            dep_collection_key = "collections"
            if dep_collection_key not in metadata:
                continue
            dep_collections_in_this_role = metadata.get(
                dep_collection_key, []
            )
            if not isinstance(dep_collections_in_this_role, list):
                continue
            dep_collections.extend(dep_collections_in_this_role)
        load_files = []
        for dep_collection in dep_collections:
            if not isinstance(dep_collection, str):
                continue
            collection_name = dep_collection
            index_file = os.path.join(
                collection_search_path,
                "collection-{}-index-ext.json".format(collection_name),
            )
            if not os.path.exists(index_file):
                continue
            index_data = json.load(open(index_file, "r"))
            _load_files_for_this_collection = index_data.get(
                "generated_load_files", []
            )
            for load_data in _load_files_for_this_collection:
                load_path = load_data.get("file", "")
                already_included = (
                    len(
                        [
                            True
                            for load_file in load_files
                            if load_file.get("file", "") == load_path
                        ]
                    )
                    > 0
                )
                if load_path != "" and not already_included:
                    load_files.append(load_data)
        return load_files

    def load_definition_ext(self, target_type, target_name, target_path):
        ld = self.create_load_file(target_type, target_name, target_path)
        output_dir = self.get_definition_path(ld.target_type, ld.target_name)
        defs_and_maps = self._parser.run(
            load_data=ld, output_dir=output_dir, use_cache=True
        )

        key = "{}-{}".format(target_type, target_name)
        self.ext_definitions[key] = defs_and_maps

    # def load_definitions_ext(self):

    #     load_file_info_list = self.index.get("generated_load_files", [])

    #     all_definitions = {}

    #     self._parser = Parser(do_save=self.do_save)

    #     num = len(load_file_info_list)
    #     if num == 0:
    #         logging.info("no target dirs found. exitting.")
    #         sys.exit()
    #     else:
    #         load_file_info = load_file_info_list[0]
    #         target_type = load_file_info.get("type", "")
    #         logging.info("start loading {} {}(s)".format(num, target_type))

    #     for i, load_file_info in enumerate(
    #         load_file_info_list
    #     ):

    #         target_type = load_file_info.get("type", "")
    #         target_name = load_file_info.get("name", "")
    #         target_path = self.get_source_path(target_type, target_name)

    #         print(
    #             "[{}/{}] {} {}".format(i + 1, num, target_type, target_name)
    #         )

    #         defs_and_maps = self._load_definition_ext(target_type, target_name, target_path)
    #         key = "{}-{}".format(target_type, target_name)
    #         all_definitions[key] = defs_and_maps

    #     return all_definitions

    def load_definitions_root(self):

        output_path = self.path_mappings.get("root_definitions", "")
        print("output_path={}".format(output_path))
        root_load = self._set_load_root()

        p = Parser(do_save=self.do_save)

        print("{}       ".format(root_load.target_name))

        defs_and_maps = p.run(
            load_data=root_load, output_dir=output_path
        )
        self.root_definitions = defs_and_maps

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
                if (
                    src == ""
                    or not os.path.exists(src)
                    or not os.path.isdir(src)
                ):
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
            raise ValueError(
                "{} is invalid definition directory".format(dir1)
            )

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

    def tree(self, root_definitions, ext_definitions, index):
        tl = TreeLoader(root_definitions, ext_definitions, index)
        trees, node_objects = tl.run()
        if trees is None:
            raise ValueError("failed to get trees")
        if node_objects is None:
            raise ValueError("failed to get node_objects")
        return trees, node_objects

    def resolve(self, trees, node_objects):
        tasks_rv = []
        num = len(trees)
        for i, tree in enumerate(trees):
            if not isinstance(tree, TreeNode):
                continue
            root_key = tree.key
            tasks = resolve_variables(tree, node_objects)
            d = {
                "root_key": tree.key,
                "tasks": tasks,
            }
            tasks_rv.append(d)
            logging.debug("resolve_variables() {}/{} ({}) done".format(i+1, num, root_key))
        return tasks_rv


def install_galaxy_target(target, target_type, output_dir):
    if (
        target_type != ContainerType.COLLECTION
        and target_type != ContainerType.ROLE
    ):
        raise ValueError("Invalid target_type: {}".format(target_type))
    proc = subprocess.run(
        "ansible-galaxy {} install {} -p {}".format(
            target_type, target, output_dir
        ),
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    install_msg = proc.stdout
    print("STDOUT: {}".format(install_msg))
    return proc.stdout


def install_github_target(target, target_type, output_dir):
    if target_type != ContainerType.PROJECT:
        raise ValueError("Invalid target_type: {}".format(target_type))
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


def escape_url(url: str):
    base_url = url.split("?")[0]
    replaced = base_url.replace("://", "__").replace("/", "_")
    return replaced


if __name__ == "__main__":
    __target_type = sys.argv[1]
    __target_name = sys.argv[2]
    __dependency_dir = ""
    if len(sys.argv) >= 4:
        __dependency_dir = sys.argv[3]
    c = DataContainer(
        type=__target_type,
        name=__target_name,
        root_dir=config.data_dir,
        dependency_dir=__dependency_dir,
    )
    c.load()
