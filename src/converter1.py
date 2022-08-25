import argparse
import sys
import json
import jsonpickle
import logging
from struct5 import ObjectList, detect_type, ExecutableType, Repository, Playbook
from tree import TreeNode, key_to_file_name, load_node_objects, TreeLoader, TreeNode, load_all_definitions
from context import Context, resolve_module_options, get_all_variables

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

            #obj["children_types"] = list(children_per_type.keys())
            if "playbook" in children_per_type:
                obj["playbooks"] = [ getSubTree(c) for c in children_per_type["playbook"] ]
            if "play" in children_per_type:
                obj["plays"] = [ getSubTree(c) for c in children_per_type["play"] ]
            if "role" in children_per_type:
                obj["roles"] = [ getSubTree(c) for c in children_per_type["role"]]
            if "taskfile" in children_per_type:
                obj["taskfiles"] = [ getSubTree(c) for c in children_per_type["taskfile"]]
            if "task" in children_per_type:
                obj["tasks"] = [ getSubTree(c) for c in children_per_type["task"]]
            if "module" in children_per_type:
                tmp_children = [getSubTree(c) for c in children_per_type["module"]]
                obj["resolved_name"] = tmp_children[0]["fqcn"] if len(tmp_children) > 0 else ""
        # end
        return obj

    tObj = getSubTree(tree, root=True)
    tObj["dependent_collections"] = list(set([ no.collection for no in _no_in_this_tree.items if hasattr(no, "collection") and no.collection != ""]))
    tObj["dependent_roles"] = list(set([ no.role for no in _no_in_this_tree.items if hasattr(no, "collection") and hasattr(no, "role") and no.collection == "" and no.role != ""]))
    tObj["dependent_module_collections"] = list(set([ no.collection for no in _no_in_this_tree.items if detect_type(no.key)=="module" and hasattr(no, "collection") and no.collection != ""]))
    # tObj["dependent_module_roles"] = list(set([ no["role"] for no in node_objects if detect_type(no["key"])=="Module" and "collection" not in no]))

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

def main():
    parser = argparse.ArgumentParser(
        prog='converter1.py',
        description='converter1',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--tree-file', default="", help='path to tree json file')
    parser.add_argument('-n', '--node-file', default="", help='path to node object json file')
    parser.add_argument('-r', '--root-dir', default="", help='path to definitions dir for root')
    parser.add_argument('-e', '--ext-dir', default="", help='path to definitions dir for ext')
    parser.add_argument('-o', '--output', default="", help='path to output file')

    args = parser.parse_args()

    if args.tree_file == "":
        logging.error("\"--tree-file\" is required")
        sys.exit(1)

    if args.node_file == "" and (args.root_dir == "" or args.ext_dir == ""):
        logging.error("\"--root-dir\" and \"--ext-dir\" are required when \"--node-file\" is empty")
        sys.exit(1)

    trees = load_tree_json(args.tree_file)
    objects = load_node_objects(args.node_file, args.root_dir, args.ext_dir)

    tree_object_lines = []
    for tree in trees:
        t_obj = convert(tree, objects)
        tree_object_lines.append(json.dumps(t_obj))
        print(json.dumps(t_obj), flush=True)

    if args.output != "":
        open(args.output, "w").write("\n".join(tree_object_lines))

if __name__ == "__main__":
    main()