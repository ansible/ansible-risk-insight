import argparse
import sys
import json
import logging
from tabulate import tabulate
from keyutil import detect_type
from models import ObjectList, ExecutableType, Repository, Playbook, Task
from tree import (
    TreeNode,
    load_all_definitions
)


def convert(tree, node_objects):
    node_dict = {}
    for no in node_objects.items:
        node_dict[no.key] = no

    _no_in_this_tree = ObjectList()

    def getSubTree(node, root=False):
        obj = {}
        no = node_dict[node.key]
        node_type = detect_type(node.key)
        _no_in_this_tree.add(no)

        # define here
        obj["type"] = node_type
        if root:
            obj["path"] = no.defined_in

        if node_type == "module":
            obj["fqcn"] = no.fqcn
        else:
            if hasattr(no, "name"):
                obj["name"] = no.name
            if hasattr(no, "fqcn"):
                obj["fqcn"] = no.fqcn

            if node_type == "task":
                if no.executable_type == ExecutableType.MODULE_TYPE:
                    obj["resolved_name"] = no.resolved_name

            children_per_type = {}
            for c in node.children:
                ctype = detect_type(c.key)
                if ctype in children_per_type:
                    children_per_type[ctype].append(c)
                else:
                    children_per_type[ctype] = [c]

            # obj["children_types"] = list(children_per_type.keys())
            if "playbook" in children_per_type:
                obj["playbooks"] = [
                    getSubTree(c) for c in children_per_type["playbook"]
                ]
            if "play" in children_per_type:
                obj["plays"] = [
                    getSubTree(c) for c in children_per_type["play"]
                ]
            if "role" in children_per_type:
                obj["roles"] = [
                    getSubTree(c) for c in children_per_type["role"]
                ]
            if "taskfile" in children_per_type:
                obj["taskfiles"] = [
                    getSubTree(c) for c in children_per_type["taskfile"]
                ]
            if "task" in children_per_type:
                obj["tasks"] = [
                    getSubTree(c) for c in children_per_type["task"]
                ]
            if "module" in children_per_type:
                tmp_children = [
                    getSubTree(c) for c in children_per_type["module"]
                ]
                obj["resolved_name"] = (
                    tmp_children[0]["fqcn"] if len(tmp_children) > 0 else ""
                )
        # end
        return obj

    tObj = getSubTree(tree, root=True)
    tObj["dependent_collections"] = list(
        set(
            [
                no.collection
                for no in _no_in_this_tree.items
                if hasattr(no, "collection") and no.collection != ""
            ]
        )
    )
    tObj["dependent_roles"] = list(
        set(
            [
                no.role
                for no in _no_in_this_tree.items
                if hasattr(no, "collection")
                and hasattr(no, "role")
                and no.collection == ""
                and no.role != ""
            ]
        )
    )
    tObj["dependent_module_collections"] = list(
        set(
            [
                no.collection
                for no in _no_in_this_tree.items
                if detect_type(no.key) == "module"
                and hasattr(no, "collection")
                and no.collection != ""
            ]
        )
    )
    return tObj


def get_inventories(playbook_key, node_objects):
    projects = node_objects.find_by_type("repository")
    inventories = []
    found = False
    for p in projects:
        if not isinstance(p, Repository):
            continue
        for playbook in p.playbooks:
            if isinstance(playbook, str):
                if playbook == playbook_key:
                    inventories = p.inventories
                    found = True
            elif isinstance(playbook, Playbook):
                if playbook.key == playbook_key:
                    inventories = p.inventories
                    found = True
            if found:
                break
        if found:
            break
    return inventories

def load_tree_json(tree_path):
    trees = []
    with open(tree_path, "r") as file:
        for line in file:
            d = json.loads(line)
            src_dst_array = d.get("tree", [])
            tree = TreeNode.load(graph=src_dst_array)
            trees.append(tree)
    return trees

def load_node_objects(node_path="", root_dir="", ext_dir=""):
    objects = ObjectList()
    if node_path != "":
        objects.from_json(fpath=node_path)
    else:
        root_defs = load_all_definitions(root_dir)
        ext_defs = load_all_definitions(ext_dir)
        for type_key in root_defs:
            objects.merge(root_defs[type_key])
            objects.merge(ext_defs[type_key])
    return objects


def check(tree: TreeNode, objects: ObjectList, verified_collections: list):
    t_obj = convert(tree, objects)
    dependencies = t_obj["dependent_module_collections"]
    unverified_dependencies = [
        d
        for d in dependencies
        if d != "ansible.builtin" and d not in verified_collections
    ]
    only_verified = len(unverified_dependencies) == 0
    ok = only_verified
    findings = (
        "all dependencies are verified"
        if only_verified
        else "depends on {} unverifeid collections".format(
            len(unverified_dependencies)
        )
    )
    resolution = (
        ""
        if only_verified
        else "the following must be signed {}".format(unverified_dependencies)
    )
    return ok, findings, resolution, t_obj


def check_tasks(tasks: list, verified_collections: list):
    if len(tasks) == 0:
        return [], []
    _tasks = [t for t in tasks]
    if isinstance(tasks[0], Task):
        _tasks = [t.__dict__ for t in tasks]
    modules = [
        t.get("resolved_name", "")
        for t in _tasks
        if t.get("executable_type", "") == "Module"
        and t.get("resolved_name", "") != ""
    ]
    dependencies = [".".join(m.split(".")[:-1]) for m in modules if "." in m]
    dependencies = list(set(dependencies))
    dependencies = sorted(dependencies)
    verified_dependencies = [
        d
        for d in dependencies
        if d == "ansible.builtin" or d in verified_collections
    ]
    unverified_dependencies = [
        d
        for d in dependencies
        if d != "ansible.builtin" and d not in verified_collections
    ]
    return verified_dependencies, unverified_dependencies


def main():
    parser = argparse.ArgumentParser(
        prog="converter1.py",
        description="converter1",
        epilog="end",
        add_help=True,
    )

    parser.add_argument(
        "-t", "--tree-file", default="", help="path to tree json file"
    )
    parser.add_argument(
        "-n", "--node-file", default="", help="path to node object json file"
    )
    parser.add_argument(
        "-r",
        "--root-dir",
        default="",
        help="path to definitions dir for root",
    )
    parser.add_argument(
        "-e", "--ext-dir", default="", help="path to definitions dir for ext"
    )
    parser.add_argument(
        "-v",
        "--verified-collections",
        default="",
        help="comma separated list of verified collections",
    )

    args = parser.parse_args()

    if args.tree_file == "":
        logging.error('"--tree-file" is required')
        sys.exit(1)

    if args.node_file == "" and (args.root_dir == "" or args.ext_dir == ""):
        logging.error(
            '"--root-dir" and "--ext-dir" are required when "--node-file" is'
            " empty"
        )
        sys.exit(1)

    trees = load_tree_json(args.tree_file)
    objects = load_node_objects(args.node_file, args.root_dir, args.ext_dir)

    verified_collections = [
        d.replace(" ", "")
        for d in args.verified_collections.split(",")
        if d.replace(" ", "") != ""
    ]

    table = [["Type", "Name", "Result", "Findings", "Resolution"]]
    for tree in trees:
        root_type = detect_type(tree.key)
        ok, findings, resolution, t_obj = check(
            tree, objects, verified_collections
        )
        single_result = [
            root_type,
            t_obj["path"],
            "o" if ok else "x",
            findings,
            resolution,
        ]
        table.append(single_result)
    print(tabulate(table))


if __name__ == "__main__":
    main()
