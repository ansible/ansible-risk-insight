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
from gen_report import gen_report
from show_report import make_display_report


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)


class Config:
    data_dir: str = os.environ.get(
        "ARI_DATA_DIR", os.path.join(os.environ["HOME"], ".ari/data")
    )


config = Config()


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
    root_load: Load = Load()
    ext_load: list = field(default_factory=list)

    root_definitions: dict = field(default_factory=dict)
    ext_definitions: dict = field(default_factory=dict)

    trees: list = field(default_factory=list)
    node_objects: ObjectList = ObjectList()

    tasks_rv: list = field(default_factory=list)

    detail_report: list = field(default_factory=list)
    report_to_display: str = ""

    # TODO: remove attributes below once refactoring is done
    root_dir: str = ""
    path_mappings: dict = field(default_factory=dict)

    dependency_dir: str = ""

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
                self.type,
                self.name,
            ),
            "ext_load": os.path.join(
                self.root_dir,
                type_root,
                "ext",
                "load-{}-{}.json".format(self.type, self.name),
            ),
            "ext_definitions": os.path.join(
                self.root_dir, type_root, "definitions"
            ),
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
        try:
            self.setup_tmp_dir()
            self.install()
        finally:
            self.clean_tmp_dir()
        self.set_load()
        ext_definitions_dir = self.path_mappings.get("ext_definitions", "")
        root_definitions_dir = self.path_mappings.get("root_definitions", "")
        self.set_definitions(ext_definitions_dir, root_definitions_dir)
        self.set_trees()
        self.set_resolved()
        self.set_detail_report()
        self.set_report()
        dep_num, ext_counts, root_counts = self.count_definitions()
        print("# of dependencies:", dep_num)
        print("ext definitions:", ext_counts)
        print("root definitions:", root_counts)

        print("---- ARI report ----")
        print(self.report_to_display)
        return

    def set_src(self, src_location):
        self.src = src_location

    def get_src(self):
        return self.src

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

        self.move_src(tmp_src_dir, dst_src_dir)
        if dst_dependency_dir != "":
            self.move_src(dependency_dir, dst_dependency_dir)
        return

    def get_index(self):
        return self.index

    def set_load(self):
        load_file_info_list = self.index.get("generated_load_files", [])
        target_list = []
        for load_file_info in load_file_info_list:
            ext_type = load_file_info.get("type", "")
            ext_name = load_file_info.get("name", "")
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
            target_list.append((ext_type, ext_name, target_path))
        type_root = self.type + "s"
        ext_dir = os.path.join(self.root_dir, type_root, "ext")

        load_data_list = self.create_load_files(True, target_list, ext_dir)
        self.ext_load = load_data_list

        root_target_list = []
        root_dir = os.path.join(self.root_dir, type_root, "root")
        if self.type in [ContainerType.ROLE, ContainerType.COLLECTION]:
            for (ext_type, ext_name, target_path) in target_list:
                if ext_type == self.type and ext_name == self.name:
                    root_target_list = [(ext_type, ext_name, target_path)]
                    break
        elif self.type == ContainerType.PROJECT:
            dst_src_dir = os.path.join(self.src, escape_url(self.name))
            root_target_list = [(self.type, self.name, dst_src_dir)]
        root_load_data_list = self.create_load_files(
            False, root_target_list, root_dir
        )
        self.root_load = root_load_data_list[0]
        return

    def get_load(self):
        return self.root_load, self.ext_load

    def set_definitions(self, ext_definitions_dir, root_definitions_dir):
        print("decomposing files")
        self.ext_definitions = self.load_definitions(
            True, ext_definitions_dir
        )
        self.root_definitions = self.load_definitions(
            False, root_definitions_dir
        )

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

    def set_detail_report(self):
        report = gen_report(self.tasks_rv, [], False)
        self.detail_report = report
        return

    def get_detail_report(self):
        return self.detail_report

    def set_report(self):
        report_txt = make_display_report(detail_report=self.detail_report)
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

    def create_load_files(self, is_ext, target_list, output_path):
        num = len(target_list)
        if num == 0:
            logging.info("no target dirs found. exitting.")
            sys.exit()
        else:
            target_type = target_list[0][0]
            logging.info("start loading {} {}(s)".format(num, target_type))

        loader_version = get_loader_version()

        load_list = []
        for i, (target_type, target_name, target_path) in enumerate(
            target_list
        ):
            print(
                "[{}/{}] {} {}".format(i + 1, num, target_type, target_name)
            )

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
            load_list.append(ld)
        return load_list

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

    def load_definitions(self, is_ext, output_path):

        profiles = []
        if is_ext:
            profiles = [
                (
                    ld,
                    os.path.join(
                        output_path,
                        "{}-{}".format(ld.target_type, ld.target_name),
                    ),
                )
                for ld in self.ext_load
            ]
        else:
            profiles = [(self.root_load, output_path)]

        num = len(profiles)
        if num == 0:
            logging.info("no load json files found. exitting.")
            sys.exit()
        else:
            logging.info("start parsing {} target(s)".format(num))

        all_definitions = {}
        p = Parser()
        for i, (load_data, output_dir) in enumerate(profiles):
            print(
                "[{}/{}] {}       ".format(i + 1, num, load_data.target_name)
            )
            key = "{}-{}".format(load_data.target_type, load_data.target_name)
            definitions, mappings = p.run(
                load_data=load_data, output_dir=output_dir
            )
            if is_ext:
                all_definitions[key] = {
                    "definitions": definitions,
                    "mappings": mappings,
                }
            else:
                all_definitions = {
                    "definitions": definitions,
                    "mappings": mappings,
                }
        return all_definitions

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
        for tree in trees:
            if not isinstance(tree, TreeNode):
                continue
            tasks = resolve_variables(tree, node_objects)
            d = {
                "root_key": tree.key,
                "tasks": tasks,
            }
            tasks_rv.append(d)
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
    target_type = sys.argv[1]
    target_name = sys.argv[2]
    dependency_dir = ""
    if len(sys.argv) >= 4:
        dependency_dir = sys.argv[3]
    c = DataContainer(
        type=target_type,
        name=target_name,
        root_dir=config.data_dir,
        dependency_dir=dependency_dir,
    )
    c.load()
