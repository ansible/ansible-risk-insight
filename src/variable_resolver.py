import argparse
import os
import sys
import json
import logging
from keyutil import detect_type
from models import ObjectList, ExecutableType, Repository, Playbook, Role
from tree import TreeNode, load_all_definitions
from context import Context, resolve_module_options


def tree_to_task_list(tree, node_objects):
    node_dict = {}
    for no in node_objects.items:
        node_dict[no.key] = no

    def getSubTree(node):
        tasks = []
        resolved_name = ""
        no = node_dict[node.key]
        node_type = detect_type(node.key)

        children_tasks = []
        if node_type == "module":
            resolved_name = no.fqcn
        elif node_type == "role":
            resolved_name = no.fqcn
        elif node_type == "taskfile":
            resolved_name = no.key

        children_per_type = {}
        for c in node.children:
            ctype = detect_type(c.key)
            if ctype in children_per_type:
                children_per_type[ctype].append(c)
            else:
                children_per_type[ctype] = [c]

        # obj["children_types"] = list(children_per_type.keys())
        if "playbook" in children_per_type:
            tasks_per_children = [
                getSubTree(c) for c in children_per_type["playbook"]
            ]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
        if "play" in children_per_type:
            tasks_per_children = [
                getSubTree(c) for c in children_per_type["play"]
            ]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
        if "role" in children_per_type:
            tasks_per_children = [
                getSubTree(c) for c in children_per_type["role"]
            ]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
            if node_type == "task":
                fqcns = [fqcn for (_, fqcn) in tasks_per_children]
                resolved_name = fqcns[0] if len(fqcns) > 0 else ""
        if "taskfile" in children_per_type:
            tasks_per_children = [
                getSubTree(c) for c in children_per_type["taskfile"]
            ]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
            if node_type == "task":
                _tf_path_list = [
                    _tf_path for (_, _tf_path) in tasks_per_children
                ]
                resolved_name = (
                    _tf_path_list[0] if len(_tf_path_list) > 0 else ""
                )
        if "task" in children_per_type:
            tasks_per_children = [
                getSubTree(c) for c in children_per_type["task"]
            ]
            for (_tasks, _) in tasks_per_children:
                children_tasks.extend(_tasks)
        if "module" in children_per_type:
            if node_type == "task":
                fqcns = [
                    getSubTree(c)[1] for c in children_per_type["module"]
                ]
                resolved_name = fqcns[0] if len(fqcns) > 0 else ""

        if node_type == "task":
            no.resolved_name = resolved_name
            tasks.append(no.__dict__)
        tasks.extend(children_tasks)
        return tasks, resolved_name

    tasks, _ = getSubTree(tree)
    return tasks


def resolve_variables(tree, node_objects):
    node_dict = {}
    for no in node_objects.items:
        node_dict[no.key] = no

    def add_context(node, context, contexts_per_task, depth_level=0):
        current_context = context.copy()
        node_type = detect_type(node.key)
        obj = node_dict[node.key]
        current_context.add(obj, depth_level)
        if node_type == "task":
            # insert "resolved_name" to task obj
            if len(node.children) > 0:
                c = node.children[0]
                c_obj = node_dict.get(c.key, None)
                if c_obj is not None:
                    if obj.executable_type == ExecutableType.MODULE_TYPE:
                        obj.resolved_name = c_obj.fqcn
                    elif obj.executable_type == ExecutableType.ROLE_TYPE:
                        obj.resolved_name = c_obj.fqcn
                    elif obj.executable_type == ExecutableType.TASKFILE_TYPE:
                        obj.resolved_name = c_obj.key
            contexts_per_task.append((current_context, obj))
        for c in node.children:
            contexts_per_task = add_context(
                c, current_context, contexts_per_task, depth_level + 1
            )
            current_context = contexts_per_task[-1][0]
        return contexts_per_task

    # if load type is "project", it might have inventories
    # otherwise, it will be just an empty list
    inventories = get_inventories(tree.key, node_objects)
    initial_context = Context(inventories=inventories)
    contexts_per_task = []
    contexts_per_task = add_context(tree, initial_context, contexts_per_task)

    tasks = []
    for (ctx, task) in contexts_per_task:
        (
            resolved_options,
            resolved_variables,
            mutable_vars_per_mo,
        ) = resolve_module_options(ctx, task)
        task.resolved_variables = resolved_variables
        task.mutable_vars_per_mo = mutable_vars_per_mo
        task.resolved_module_options = resolved_options
        tasks.append(task.__dict__)
    return tasks


def get_inventories(tree_root_key, node_objects):
    tree_root_type = detect_type(tree_root_key)
    projects = node_objects.find_by_type("repository")
    inventories = []
    found = False
    for p in projects:
        if not isinstance(p, Repository):
            continue
        if tree_root_type == "playbook":
            for playbook in p.playbooks:
                if isinstance(playbook, str):
                    if playbook == tree_root_key:
                        inventories = p.inventories
                        found = True
                elif isinstance(playbook, Playbook):
                    if playbook.key == tree_root_key:
                        inventories = p.inventories
                        found = True
                if found:
                    break
        elif tree_root_type == "role":
            for role in p.roles:
                if isinstance(role, str):
                    if role == tree_root_key:
                        inventories = p.inventories
                        found = True
                elif isinstance(role, Role):
                    if role.key == tree_root_key:
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


def main():
    parser = argparse.ArgumentParser(
        prog="variable_resolver.py",
        description="resolve variables",
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
        "-o", "--out-dir", default="", help="path to output dir"
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

    tasks_rv_lines = []
    for tree in trees:
        if not isinstance(tree, TreeNode):
            continue
        tasks = resolve_variables(tree, objects)
        d = {
            "root_key": tree.key,
            "tasks": tasks,
        }
        line = json.dumps(d)
        tasks_rv_lines.append(line)
    tasks_rv_path = os.path.join(args.out_dir, "tasks_rv.json")
    open(tasks_rv_path, "w").write("\n".join(tasks_rv_lines))


if __name__ == "__main__":
    main()
