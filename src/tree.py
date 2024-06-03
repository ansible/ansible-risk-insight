import argparse
import logging
import os
import re
import json
from copy import deepcopy
from dataclasses import dataclass, field
from keyutil import detect_type, key_delimiter, object_delimiter
from models import (
    ObjectList,
    Playbook,
    Play,
    RoleInPlay,
    Role,
    Task,
    TaskFile,
    ExecutableType,
    Load,
    Module,
    LoadType,
)
from finder import get_builtin_module_names

obj_type_dict = {
    "playbook": "playbooks",
    "play": "plays",
    "role": "roles",
    "taskfile": "taskfiles",
    "task": "tasks",
    "module": "modules",
}

module_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$")
role_name_re = re.compile(r"^[a-z0-9_]+\.[a-z0-9_]+$")
role_in_collection_name_re = re.compile(
    r"^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$"
)


@dataclass
class TreeNode(object):
    key: str = ""

    # children is a list of TreeNode
    children: list = field(default_factory=list)

    definition: dict = field(default_factory=dict)

    # load a list of (src, dst) as a tree structure
    # which is composed of multiple TreeNode
    @staticmethod
    def load(path="", graph=[]):
        if path != "":
            graph = []
            with open(path, "r") as file:
                graph = json.load(file)
        root_key_cands = [pair[1] for pair in graph if pair[0] is None]
        if len(root_key_cands) != 1:
            raise ValueError(
                "tree array must have only one top with src == None, but"
                " found {}".format(len(root_key_cands))
            )
        root_key = root_key_cands[0]
        tree = TreeNode()
        tree, _ = tree.recursive_tree_load(root_key, graph)
        tree.key = root_key
        tree.children = tree.children
        tree.definition = tree.definition
        return tree

    # output list of (src, dst) to stdout or file
    def dump(self, path=""):
        src_dst_array = self.to_graph()
        if path == "":
            print(json.dumps(src_dst_array, indent=2))
        else:
            tree_json = json.dumps(src_dst_array)
            with open(path, "w") as file:
                file.write(tree_json)

    def to_str(self):
        src_dst_array = self.to_graph()
        return json.dumps(src_dst_array)

    # return list of (src, dst)
    def to_graph(self):
        return self.recursive_graph_dump(None, self)

    # return list of dst keys
    def to_keys(self):
        return [p[1] for p in self.to_graph()]

    # reutrn list of TreeNodes that are under this TreeNode
    def to_list(self):
        return self.recursive_convert_to_list(self)

    def recursive_convert_to_list(self, node, nodelist=[]):
        current = [pair for pair in nodelist]
        current.append(node)
        for child_node in node.children:
            current = self.recursive_convert_to_list(child_node, current)
        return current

    def recursive_tree_load(self, node_key, src_dst_array, parent_keys=None):
        if parent_keys is None:
            parent_keys = set()
        n = TreeNode(key=node_key)
        if node_key in parent_keys:
            return n, parent_keys
        parent_keys.add(node_key)
        new_parent_keys = parent_keys.copy()
        for (src_key, dst_key) in src_dst_array:
            children_keys = []
            if node_key == src_key:
                children_keys.append(dst_key)
            for c_key in children_keys:
                child_tree, sub_parent_keys = self.recursive_tree_load(
                    c_key, src_dst_array, parent_keys
                )
                n.children.append(child_tree)
                new_parent_keys = new_parent_keys.union(sub_parent_keys)
        return n, new_parent_keys

    def recursive_graph_dump(self, parent_node, node, src_dst_array=[]):
        current = [pair for pair in src_dst_array]
        src = None if parent_node is None else parent_node.key
        dst = node.key
        current.append((src, dst))
        for child_node in node.children:
            is_included = (
                len(
                    [
                        (src, dst)
                        for (src, dst) in current
                        if src == child_node.key
                    ]
                )
                > 0
            )
            if is_included:
                continue
            current = self.recursive_graph_dump(node, child_node, current)
        return current

    # return a list of (src, dst) which ends with the "end_key"
    # this could return multiple paths
    def path_to_root(self, end_key):
        path_array = self.search_branch_to_key(end_key, self)
        path_array = [nodelist2branch(nodelist) for nodelist in path_array]
        return path_array

    def search_branch_to_key(self, search_key, node, ancestors=[]):
        current = [n for n in ancestors]
        found = []
        if node.key == search_key:
            found = current + [node]
        for child_node in node.children:
            found_in_child = self.search_branch_to_key(
                search_key, child_node, current + [node]
            )
            found.extend(found_in_child)
        return found

    def copy(self):
        return deepcopy(self)

    @property
    def is_empty(self):
        return self.key == "" and len(self.children) == 0

    @property
    def has_definition(self):
        return len(self.definition) == 0


def nodelist2branch(nodelist):
    if len(nodelist) == 0:
        return TreeNode()
    t = nodelist[0].copy()
    current = t
    for i, n in enumerate(nodelist):
        if i == 0:
            continue
        current.children = [n.copy()]
        current = current.children[0]
    return t


def load_graph(graph_path):
    graph = {}
    with open(graph_path, "r") as file:
        for line in file:
            edge = json.loads(line)
            src = edge[0]
            dst = edge[1]
            children = graph.get(src, [])
            children.append(dst)
            graph[src] = children
    return graph


def load_single_definition(defs: dict, key: str):
    obj_list = ObjectList()
    items = defs.get(key, [])
    for item in items:
        obj_list.add(item)
    return obj_list


def load_definitions(defs: dict, types: list):
    def_list = []
    for type_key in types:
        objs_per_type = load_single_definition(defs, type_key)
        def_list.append(objs_per_type)
    return def_list


def load_all_definitions(definitions: dict, dependencies: list = []):
    _definitions = {}
    if "mappings" in definitions:
        _definitions = {"root": definitions}
    else:
        _definitions = definitions
    loaded = {}
    types = ["roles", "taskfiles", "modules", "playbooks", "plays", "tasks"]
    for _, definitions_per_artifact in _definitions.items():
        def_list = load_definitions(
            definitions_per_artifact.get("definitions", {}), types
        )
        for i, type_key in enumerate(types):
            if type_key not in loaded:
                loaded[type_key] = def_list[i]
            else:
                loaded[type_key].merge(def_list[i])
    return loaded


def load_mappings(fpath):
    ld = Load()
    ld.from_json(open(fpath, "r").read())
    return ld


def make_dicts(root_definitions, ext_definitions):
    definitions = {
        "roles": ObjectList(),
        "modules": ObjectList(),
        "taskfiles": ObjectList(),
        "playbooks": ObjectList(),
    }
    for type_key in definitions:
        definitions[type_key].merge(
            root_definitions.get(type_key, ObjectList())
        )
        definitions[type_key].merge(
            ext_definitions.get(type_key, ObjectList())
        )
    dicts = {}
    for type_key, obj_list in definitions.items():
        for obj in obj_list.items:
            obj_dict_key = obj.fqcn if hasattr(obj, "fqcn") else obj.key
            if type_key not in dicts:
                dicts[type_key] = {}
            dicts[type_key][obj_dict_key] = obj
    return dicts


def resolve(obj, dicts):
    failed = False
    if isinstance(obj, Task):
        task = obj
        if task.executable != "":
            if task.executable_type == ExecutableType.MODULE_TYPE:
                task.resolved_name = resolve_module(
                    task.executable, dicts.get("modules", {})
                )
            elif task.executable_type == ExecutableType.ROLE_TYPE:
                task.resolved_name = resolve_role(
                    task.executable,
                    dicts.get("roles", {}),
                    task.collection,
                    task.collections_in_play,
                )
            elif task.executable_type == ExecutableType.TASKFILE_TYPE:
                task.resolved_name = resolve_taskfile(
                    task.executable, dicts.get("taskfiles", {}), task.key
                )
            if task.resolved_name == "":
                failed = True
    elif isinstance(obj, Play):
        for i in range(len(obj.roles)):
            roleinplay = obj.roles[i]
            if not isinstance(roleinplay, RoleInPlay):
                continue
            roleinplay.resolved_name = resolve_role(
                roleinplay.name,
                dicts.get("roles", {}),
                roleinplay.collection,
                roleinplay.collections_in_play,
            )
            obj.roles[i] = roleinplay
            if roleinplay.resolved_name == "":
                failed = True
    return obj, failed


def resolve_module(module_name, module_dict={}):
    module_key = ""
    found_module = module_dict.get(module_name, None)
    if found_module is not None:
        module_key = found_module.key
    if module_key == "":
        for k in module_dict:
            suffix = ".{}".format(module_name)
            if k.endswith(suffix):
                module_key = module_dict[k].key
                break
    return module_key


def resolve_role(
    role_name, role_dict={}, my_collection_name="", collections_in_play=[]
):
    role_key = ""
    if "." not in role_name and len(collections_in_play) > 0:
        for coll in collections_in_play:
            role_name_cand = "{}.{}".format(coll, role_name)
            found_role = role_dict.get(role_name_cand, None)
            if found_role is not None:
                role_key = found_role.key
    else:
        if "." not in role_name and my_collection_name != "":
            role_name_cand = "{}.{}".format(my_collection_name, role_name)
            found_role = role_dict.get(role_name_cand, None)
            if found_role is not None:
                role_key = found_role.key
        if role_key == "":
            found_role = role_dict.get(role_name, None)
            if found_role is not None:
                role_key = found_role.key
            else:
                for k in role_dict:
                    suffix = ".{}".format(role_name)
                    if k.endswith(suffix):
                        role_key = role_dict[k].key
                        break
    return role_key


def resolve_taskfile(taskfile_ref, taskfile_dict={}, task_key=""):
    type_prefix = "task "
    parts = task_key[len(type_prefix):].split(object_delimiter)
    parent_key = ""
    task_defined_path = ""
    for p in parts[::-1]:
        if p.startswith("playbook" + key_delimiter) or p.startswith(
            "taskfile" + key_delimiter
        ):
            task_defined_path = p.split(key_delimiter)[1]
            parent_key = task_key[len(type_prefix):].split(p)[0]
            break

    # include/import tasks can have a path like "roles/xxxx/tasks/yyyy.yml"
    # then try to find roles directory
    if taskfile_ref.startswith("roles/"):
        if "roles/" in task_defined_path:
            roles_parent_dir = task_defined_path.split("roles/")[0]
            fpath = os.path.join(roles_parent_dir, taskfile_ref)
            fpath = os.path.normpath(fpath)
            taskfile_key = "taskfile {}taskfile{}{}".format(
                parent_key, key_delimiter, fpath
            )
            found_tf = taskfile_dict.get(taskfile_key, None)
            if found_tf is not None:
                return found_tf.key

    task_dir = os.path.dirname(task_defined_path)
    fpath = os.path.join(task_dir, taskfile_ref)
    # need to normalize path here because taskfile_ref can be
    # something like "../some_taskfile.yml".
    # it should be "tasks/some_taskfile.yml"
    fpath = os.path.normpath(fpath)
    taskfile_key = "taskfile {}taskfile{}{}".format(
        parent_key, key_delimiter, fpath
    )
    found_tf = taskfile_dict.get(taskfile_key, None)
    if found_tf is not None:
        return found_tf.key

    return ""


def resolve_playbook(playbook_ref, playbook_dict={}, play_key=""):
    type_prefix = "play "
    parts = play_key[len(type_prefix):].split(object_delimiter)
    parent_key = ""
    play_defined_path = ""
    for p in parts[::-1]:
        if p.startswith("playbook" + key_delimiter):
            play_defined_path = p.split(key_delimiter)[1]
            parent_key = play_key[len(type_prefix):].split(p)[0]
            break

    play_dir = os.path.dirname(play_defined_path)
    fpath = os.path.join(play_dir, playbook_ref)
    # need to normalize path here because playbook_ref can be
    # something like "../some_playbook.yml"
    fpath = os.path.normpath(fpath)
    playbook_key = "playbook {}playbook{}{}".format(
        parent_key, key_delimiter, fpath
    )
    found_playbook = playbook_dict.get(playbook_key, None)
    if found_playbook is not None:
        return found_playbook.key
    return ""


def init_builtin_modules():
    builtin_module_names = get_builtin_module_names()
    modules = []
    for module_name in builtin_module_names:
        collection_name = "ansible.builtin"
        fqcn = "{}.{}".format(collection_name, module_name)
        global_key = "module collection{}{}{}module{}{}".format(
            key_delimiter,
            collection_name,
            object_delimiter,
            key_delimiter,
            fqcn,
        )
        local_key = "module module{}{}".format(key_delimiter, "__builtin__")
        m = Module(
            name=module_name,
            fqcn=fqcn,
            key=global_key,
            local_key=local_key,
            collection=collection_name,
            builtin=True,
        )
        modules.append(m)
    return modules


class TreeLoader(object):
    def __init__(self, root_definitions, ext_definitions, index):

        self.load_and_mapping = root_definitions.get("mappings", None)
        self.playbook_mappings = self.load_and_mapping.playbooks
        self.role_mappings = self.load_and_mapping.roles

        dependencies = []
        # TODO: dependency check, especially for
        # collection dependencies for role

        self.org_root_definitions = root_definitions
        self.org_ext_definitions = ext_definitions

        self.root_definitions = load_all_definitions(root_definitions)
        self.ext_definitions = load_all_definitions(
            ext_definitions, dependencies
        )
        self.add_builtin_modules()

        self.dicts = make_dicts(self.root_definitions, self.ext_definitions)

        self.tree_file = ""
        self.node_file = ""

        self.trees = []
        self.node_objects = ObjectList()
        return

    def __init__backup(self, root, ext, index, tree, node):

        self.root_dir = root
        self.ext_dir = ext
        self.index_file = index
        self.tree_file = tree
        self.node_file = node

        self.load_and_mapping = load_mappings(
            os.path.join(self.root_dir, "mappings.json")
        )
        self.playbook_mappings = self.load_and_mapping.playbooks
        self.role_mappings = self.load_and_mapping.roles

        dependencies = []
        if self.index_file != "":
            index_data = json.load(open(self.index_file, "r"))
            target_type = index_data.get("target_type", "")
            out_path_in_index = index_data.get("out_path", "")
            definitions_path = out_path_in_index.replace(
                "/ext", "/definitions"
            )

            dependency_list = index_data.get("generated_load_files", [])
            for dep in dependency_list:
                if isinstance(dep, dict):
                    dep_type = dep.get("type", "")
                    dep_name = dep.get("name", "")
                    if dep_type == "" or dep_name == "":
                        continue
                    dependencies.append(
                        os.path.join(
                            definitions_path,
                            dep_name,
                        )
                    )

            if target_type == LoadType.ROLE_TYPE:
                collection_path = index_data.get("collection_path", "")
                coll_definitions_path = os.path.join(
                    collection_path, "definitions"
                )

                coll_dependency_list = index_data.get(
                    "dep_collection_load_files", []
                )
                for dep in coll_dependency_list:
                    if isinstance(dep, dict):
                        dep_type = dep.get("type", "")
                        dep_name = dep.get("name", "")
                        if dep_type == "" or dep_name == "":
                            continue
                        dependencies.append(
                            os.path.join(
                                coll_definitions_path,
                                dep_name,
                            )
                        )

        self.root_definitions = load_all_definitions(self.root_dir)
        self.ext_definitions = load_all_definitions(
            self.ext_dir, dependencies
        )
        self.add_builtin_modules()

        self.dicts = make_dicts(self.root_definitions, self.ext_definitions)
        self.trees = []
        self.node_objects = ObjectList()
        return

    def run(self):
        objects = ObjectList()
        if self.load_and_mapping.target_type == LoadType.PROJECT_TYPE:
            p_defs = self.org_root_definitions.get("definitions", {}).get(
                "projects", []
            )
            if len(p_defs) > 0:
                objects.add(p_defs[0])
            logging.info("  project loaded")
        logging.info("  start building playbook trees")
        for mapping in self.playbook_mappings:
            playbook_key = mapping[1]
            graph = [[None, playbook_key]]
            graph = self._recursive_make_graph(playbook_key, graph, objects)
            tree = TreeNode.load(graph=graph)
            self.trees.append(tree)
        logging.info("  done")
        logging.info("  start building role trees")
        for mapping in self.role_mappings:
            role_key = mapping[1]
            graph = [[None, role_key]]
            graph = self._recursive_make_graph(role_key, graph, objects)
            tree = TreeNode.load(graph=graph)
            self.trees.append(tree)
        logging.info("  done")
        self.node_objects = objects

        if self.tree_file != "":
            lines = []
            for t in self.trees:
                d = {"key": t.key, "tree": t.to_graph()}
                lines.append(json.dumps(d))
            open(self.tree_file, "w").write("\n".join(lines))
            logging.info("  tree file saved")
        if self.node_file != "":
            self.node_objects.dump(fpath=self.node_file)
            logging.info("  node file saved")
        return self.trees, self.node_objects

    def _recursive_make_graph(self, key, graph, _objects):
        current_graph = [g for g in graph]
        # if this key is already in the graph src, no need to trace children
        key_in_graph_src = [g for g in current_graph if g[0] == key]
        if len(key_in_graph_src) > 0:
            return current_graph
        # otherwise, trace children
        obj = self.get_object(key)
        if obj is None:
            return current_graph
        if not _objects.contains(obj=obj):
            _objects.add(obj)
        children_keys = self._get_children_keys(obj)
        for c_key in children_keys:
            current_graph.append([key, c_key])
            updated_graph = self._recursive_make_graph(
                c_key, current_graph, _objects
            )
            current_graph = updated_graph
        return current_graph

    def find_playbooks(self):
        return [k for k in self.graph.keys() if k.startswith("Playbook ")]

    # get definition object from root/ext definitions
    def get_object(self, obj_key):
        obj_type = detect_type(obj_key)
        if obj_type == "":
            raise ValueError(
                'failed to detect object type from key "{}"'.format(obj_key)
            )
        type_key = obj_type_dict[obj_type]
        root_definitions = self.root_definitions.get(type_key, ObjectList())
        obj = root_definitions.find_by_key(obj_key)
        if obj is not None:
            return obj
        ext_definitions = self.ext_definitions.get(type_key, ObjectList())
        obj = ext_definitions.find_by_key(obj_key)
        if obj is not None:
            return obj
        return None

    def add_builtin_modules(self):
        obj_list = ObjectList()
        builtin_modules = init_builtin_modules()
        for m in builtin_modules:
            obj_list.add(m)
        self.ext_definitions["modules"].merge(obj_list)

    def _get_children_keys(self, obj):
        children_keys = []
        if isinstance(obj, Playbook):
            children_keys = obj.plays
        elif isinstance(obj, Play):
            if obj.import_playbook != "":
                resolved_playbook_key = resolve_playbook(
                    obj.import_playbook, self.dicts["playbooks"], obj.key
                )
                if resolved_playbook_key != "":
                    children_keys.append(resolved_playbook_key)
            children_keys.extend(obj.pre_tasks)
            children_keys.extend(obj.tasks)
            for rip in obj.roles:
                resolved_role_key = resolve_role(
                    rip.name,
                    self.dicts["roles"],
                    obj.collection,
                    obj.collections_in_play,
                )
                if resolved_role_key != "":
                    children_keys.append(resolved_role_key)
            children_keys.extend(obj.post_tasks)
        elif isinstance(obj, Role):
            main_taskfile_key = [
                tf
                for tf in obj.taskfiles
                if tf.split(key_delimiter)[-1].split("/")[-1]
                in ["main.yml", "main.yaml"]
            ]
            children_keys.extend(main_taskfile_key)
        elif isinstance(obj, TaskFile):
            children_keys = obj.tasks
        elif isinstance(obj, Task):
            executable_type = obj.executable_type
            resolved_key = ""
            if executable_type == ExecutableType.MODULE_TYPE:
                resolved_key = resolve_module(
                    obj.executable, self.dicts["modules"]
                )
            elif executable_type == ExecutableType.ROLE_TYPE:
                resolved_key = resolve_role(
                    obj.executable,
                    self.dicts["roles"],
                    obj.collection,
                    obj.collections_in_play,
                )
            elif executable_type == ExecutableType.TASKFILE_TYPE:
                resolved_key = resolve_taskfile(
                    obj.executable, self.dicts["taskfiles"], obj.key
                )
            if resolved_key != "":
                children_keys.append(resolved_key)
        return children_keys

    def node_objects(self, tree):
        loaded = {}
        obj_list = ObjectList()
        for k in tree.to_keys():
            if k in loaded:
                obj_list.add(loaded[k])
                continue
            obj = self.get_object(k)
            if obj is None:
                logging.warning("object not found for the key {}".format(k))
                continue
            obj_list.add(obj)
            loaded[k] = obj
        return obj_list


def dump_node_objects(obj_list, path=""):
    if path == "":
        lines = obj_list.dump()
        for line in lines:
            obj_dict = json.loads(line)
            print(json.dumps(obj_dict, indent=2))
    else:
        obj_list.dump(fpath=path)


def load_tree_json(tree_path):
    trees = []
    with open(tree_path, "r") as file:
        for line in file:
            d = json.loads(line)
            src_dst_array = d.get("tree", [])
            tree = TreeNode.load(graph=src_dst_array)
            trees.append(tree)
    return trees


def load_node_objects(node_list_file):
    obj_list = ObjectList().from_json(fpath=node_list_file)
    return obj_list


def key_to_file_name(prefix, key):
    return (
        prefix
        + "___"
        + key.translate(str.maketrans({" ": "___", "/": "---", ".": "_dot_"}))
        + ".json"
    )


def main():

    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        prog="tree.py",
        description=(
            "make a tree of ansible nodes in graph.json and show/save it"
        ),
        epilog="end",
        add_help=True,
    )

    parser.add_argument(
        "-r",
        "--root",
        default="",
        help="path to the input definition dir for root",
    )
    parser.add_argument(
        "-e",
        "--ext",
        default="",
        help="path to the input definition dir for ext",
    )
    parser.add_argument(
        "-i",
        "--index",
        default="",
        help=(
            "path to the index.json file to specify the definitions to be"
            ' loaded in the "ext" dir'
        ),
    )
    parser.add_argument(
        "-t", "--tree", default="", help="path to the output tree file"
    )
    parser.add_argument(
        "-n",
        "--node",
        default="array",
        help="path to the output node objects",
    )

    args = parser.parse_args()

    logging.info("start initializing tree_loader")
    tree_loader = TreeLoader(
        args.root, args.ext, args.index, args.tree, args.node
    )
    logging.info("done")
    logging.info("start building trees")
    tree_loader.run()
    logging.info("done")


if __name__ == "__main__":
    main()
