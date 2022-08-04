import argparse
# from logging import root
import os
import json
import jsonpickle
from tree import TreeNode, key_to_file_name, load_node_objects, detect_type, TreeLoader
from context import Context, resolve_module_options

def convert(root_key, data_dir):

    tree_file = os.path.join(data_dir, key_to_file_name("tree", root_key))
    node_file = os.path.join(data_dir, key_to_file_name("node", root_key))

    tree = TreeNode.load(tree_file)
    node_objects = load_node_objects(node_file)

    node_dict = {}
    for no in node_objects.items:
        node_dict[no.key] = no

    def getSubTree(node):
        obj = {}
        no = node_dict[node.key]
        node_type = detect_type(node.key)

        # define here
        obj["type"] = node_type

        if node_type == "Module":
            obj["fqcn"] = no.fqcn
        else:
            # obj["key"] = no["key"]
            if "name" in obj:
                obj["name"] = no.name

            if node_type == "Task":
                obj["name"] = no.name
                # obj["role"] = no["role"]
                # obj["collection"] = no["collection"]
                # obj["definition"] = no

                if no.executable_type == "Module":
                    # obj["executable_type"] = no["executable_type"]
                    obj["resolved_name"] = no.resolved_name
                # obj["definition"] = no
            # else:
            #     obj["definition"] = no

            children_per_type = {}
            for c in node.children:
                ctype = detect_type(c.key)
                if ctype in children_per_type:
                    children_per_type[ctype].append(c)
                else:
                    children_per_type[ctype] = [c]

            #obj["children_types"] = list(children_per_type.keys())
            if "Playbook" in children_per_type:
                obj["playbooks"] = [ getSubTree(c) for c in children_per_type["Playbook"] ]
            if "Play" in children_per_type:
                obj["plays"] = [ getSubTree(c) for c in children_per_type["Play"] ]
            if "Role" in children_per_type:
                obj["roles"] = [ getSubTree(c) for c in children_per_type["Role"]]
            if "TaskFile" in children_per_type:
                obj["taskfiles"] = [ getSubTree(c) for c in children_per_type["TaskFile"]]
            if "Task" in children_per_type:
                obj["tasks"] = [ getSubTree(c) for c in children_per_type["Task"]]
        # end
        return obj

    tObj = getSubTree(tree)
    tObj["dependent_collections"] = list(set([ no.collection for no in node_objects.items if hasattr(no, "collection") and no.collection != ""]))
    tObj["dependent_roles"] = list(set([ no.role for no in node_objects.items if hasattr(no, "collection") and hasattr(no, "role") and no.collection == "" and no.role != ""]))
    tObj["dependent_module_collections"] = list(set([ no.collection for no in node_objects.items if detect_type(no.key)=="Module" and hasattr(no, "collection") and no.collection != ""]))
    # tObj["dependent_module_roles"] = list(set([ no["role"] for no in node_objects if detect_type(no["key"])=="Module" and "collection" not in no]))

    context_and_task = []
    def add_context(node, context=None, depth_level=0):
        current_context = None
        if context is None:
            current_context = Context()
        else:
            current_context = context.copy()
        node_type = detect_type(node.key)
        obj = node_dict[node.key]
        current_context.add(obj, depth_level)
        if node_type == "Task":
            context_and_task.append((current_context, obj))

        for c in node.children:
            add_context(c, current_context, depth_level+1)
    
    add_context(tree)

    contexts = []
    for (ctx, task) in context_and_task:
        resolved_options = resolve_module_options(ctx, task)
        single_item = {
            "context": ctx,
            "task": task,
            "resolved_options": resolved_options,
        }
        contexts.append(single_item)

    return tObj, contexts

def main():
    parser = argparse.ArgumentParser(
        prog='converter1.py',
        description='converter1',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--target', default="", help='target key which is the root (or leaf if reverse) of the tree')
    parser.add_argument('-d', '--dir', default="", help='path to input directory')
    parser.add_argument('-g', '--graph', default="graph.json", help='path to the graph file')

    args = parser.parse_args()

    data_dir = args.dir
    if args.target != "":
        root_key = args.target
        tObj = convert(root_key, data_dir)
        print(json.dumps(tObj, indent=2))
    elif args.graph != "":
        t = TreeLoader(args.graph)
        playbook_keys = t.find_playbooks()
        for k in playbook_keys:
            tObj = convert(k, data_dir)
            print(json.dumps(tObj, indent=2))
    else:
        raise ValueError("target or graph must be specified to show tree(s)")


if __name__ == "__main__":
    main()