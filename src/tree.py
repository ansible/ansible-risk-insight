import argparse
import logging
import os
import json
import jsonpickle
from copy import deepcopy
from dataclasses import dataclass, field
from struct5 import ObjectList, JSONSerializable


obj_type_dict = {
    "Playbook": "playbooks.json",
    "Play": "plays.json",
    "Role": "roles.json",
    "TaskFile": "taskfiles.json",
    "Task": "tasks.json",
    "Module": "modules.json",
}

@dataclass
class TreeNode(object):
    key: str = ""

    # children is a list of TreeNode
    children: list = field(default_factory=list)

    definition: dict = field(default_factory=dict)

    # load a list of (src, dst) as a tree structure which is composed of multiple TreeNode
    @staticmethod
    def load(path="", graph=[]):
        if path != "":
            graph = []
            with open(path, "r") as file:
                graph = json.load(file)
        root_key_cands = [pair[1] for pair in graph if pair[0] is None]
        if len(root_key_cands) != 1:
            raise ValueError("tree array must have only one top with src == None, but found {}".format(len(root_key_cands)))
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

    def recursive_tree_load(self, node_key, src_dst_array, visited=None):
        if visited is None:
            visited = set()
        if len(visited) == len(src_dst_array):
            return TreeNode(), visited
        n = TreeNode(key=node_key)
        for i, (src_key, dst_key) in enumerate(src_dst_array):
            if i in visited:
                continue
            children_keys = []
            if node_key == src_key:
                children_keys.append(dst_key)
                visited.add(i)
            for c_key in children_keys:
                child_tree, new_visited = self.recursive_tree_load(c_key, src_dst_array, visited)
                n.children.append(child_tree)
                visited = visited.union(new_visited)
        return n, visited

    def recursive_graph_dump(self, parent_node, node, src_dst_array=[]):
        current = [pair for pair in src_dst_array]
        src = None if parent_node is None else parent_node.key
        dst = node.key
        current.append((src, dst))
        for child_node in node.children:
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
            found_in_child = self.search_branch_to_key(search_key, child_node, current + [node])
            found.extend(found_in_child)
        return found

        
    def get_all_paths(self):
        all_paths = []
        

    def copy(self):
        return deepcopy(self)


    @property
    def is_empty(self):
        return self.key == "" and len(self.children)==0

    @property
    def has_definition(self):
        return len(self.definition)==0

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

class TreeLoader(object):

    def __init__(self, graph_path, definition_dir=""):

        self.graph = load_graph(graph_path)

        if len(self.graph) == 0:
            raise ValueError("the loaded graph is empty; something wrong")
        print("INIT0 all graph loaded")

        self.definition_cache = {}
        self.definition_dir = definition_dir
        if graph_path != "" and definition_dir == "":
            self.definition_dir = os.path.dirname(graph_path)

    def find_playbooks(self):
        return [k for k in self.graph.keys() if k.startswith("Playbook ")]

    # get definition object from each object list files
    def get_object(self, obj_key):
        obj_type = ""
        for k in obj_type_dict:
            if obj_key.startswith("{} ".format(k)):
                obj_type = k
                break
        if obj_type == "":
            raise ValueError("failed to detect object type from key \"{}\"".format(obj_key))
        definition_path = os.path.join(self.definition_dir, obj_type_dict[obj_type])
        obj = {}
        data = {}
        if definition_path in self.definition_cache:
            data = self.definition_cache[definition_path]
        else:
            obj_list = ObjectList().from_json(fpath=definition_path)
            for obj in obj_list.items:
                k = obj.key
                v = obj
                data[k] = v
            self.definition_cache[definition_path] = data
        obj = data.get(obj_key, None)
        return obj

    def make_tree(self, root_key):
        tree = TreeNode(key=root_key)
        self._recursive_add_nodes(root_key, tree.children)
        return tree

    def _recursive_add_nodes(self, key, children, ancestors=[]):
        children_keys = self._get_children(key)
        _ancestors = [a for a in ancestors]
        for child_key in children_keys:
            child_node = TreeNode(key=child_key)
            children.append(child_node)
            # if cycle is found, stop here
            if child_key in _ancestors:
                continue
            _ancestors.append(child_key)
            self._recursive_add_nodes(child_key, child_node.children, _ancestors)

    def _detect_type(self, key):
        obj_type = key.split(" ")[0]
        return obj_type

    def _get_children(self, parent_key):
        children_keys = self.graph.get(parent_key, None)
        # Tasks with empty resolved name are not listed in graph, so just skip if key was not found
        if children_keys is None:
            return []
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

def detect_type(key):
    obj_type = key.split(" ")[0]
    return obj_type

def dump_node_objects(obj_list, path=""):
    if path == "":
        lines = obj_list.dump()
        for l in lines:
            obj_dict = json.loads(l)
            print(json.dumps(obj_dict, indent=2))
    else:
        obj_list.dump(fpath=path)

def load_node_objects(node_list_file):
    obj_list = ObjectList().from_json(fpath=node_list_file)
    return obj_list


def key_to_file_name(prefix, key):
    return prefix + "___" + key.translate(str.maketrans({' ': '___', '/': '---', '.':'_dot_'}))+".json"

def main():
    parser = argparse.ArgumentParser(
        prog='tree.py',
        description='make a tree of ansible nodes in graph.json and show/save it',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-g', '--graph', default="graph.json", help='path to the graph file')
    parser.add_argument('-t', '--target', default="", help='target key which is the root (or leaf if reverse) of the tree')
    parser.add_argument('-o', '--out-file', default="", help='path to the output tree file')
    parser.add_argument('-n', '--node-file', default="array", help='path to the output node objects')
    parser.add_argument('-r', '--reverse', action='store_true', help='whether to search from leaves')
    parser.add_argument('-d', '--dir', default="", help='path to input directory')

    
    args = parser.parse_args()

    if args.reverse:
        raise ValueError("not implemented yet")

    # if args.target == "":
    #     raise ValueError("target must be specified to show tree(s)")

    if args.graph == "":
        raise ValueError("the graph path is required")

    out_dir = args.dir

    t = TreeLoader(args.graph)

    print("DEBUG0 start")

    playbook_keys = t.find_playbooks()

    for root_key in playbook_keys:
        print(root_key)

    for root_key in playbook_keys:
        print("DEBUG1 start for "+root_key)

        # root_key = args.target
        tree = t.make_tree(root_key)
        print("DEBUG2 tree constructed for "+root_key)

        node_objects = t.node_objects(tree)
        print("DEBUG3 node objects loaded for "+root_key)
        
        # output to stdout if out_file is empty
        # tree_file = args.out_file
        tree_file = os.path.join(out_dir, key_to_file_name("tree", root_key))
        tree.dump(tree_file)
        print("DEBUG4 tree saved for "+root_key)

        # node_file = args.node_file
        node_file = os.path.join(out_dir, key_to_file_name("node", root_key))
        dump_node_objects(node_objects, node_file)
        print("DEBUG5 node objects saved for "+root_key)

        # load & redump tree (just for test)
        # tree2 = TreeNode.load(tree_file)
        # tree2.dump(tree_file+"_2")

        # load & redump node_objects (just for test)
        # no2 = load_node_objects(node_file)
        # dump_node_objects(no2, node_file+"_2")

if __name__ == "__main__":
    main()