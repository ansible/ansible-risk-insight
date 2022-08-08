import argparse
import logging
import os
import sys
import re
import json
import jsonpickle
from copy import deepcopy
from dataclasses import dataclass, field
from struct5 import ObjectList, RoleInPlay, Task, Play, ExecutableType, BuiltinModuleSet, object_delimiter, key_delimiter


obj_type_dict = {
    "Playbook": "playbooks.json",
    "Play": "plays.json",
    "Role": "roles.json",
    "TaskFile": "taskfiles.json",
    "Task": "tasks.json",
    "Module": "modules.json",
}

module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')
role_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+$')
role_in_collection_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

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

def load_single_definition(fpath):
        obj_list = ObjectList()
        if os.path.exists(fpath):
            obj_list.from_json(fpath=fpath)
        return obj_list

def load_definitions(dir):
    roles = load_single_definition(os.path.join(dir, "roles.json"))
    taskfiles = load_single_definition(os.path.join(dir, "taskfiles.json"))
    modules = load_single_definition(os.path.join(dir, "modules.json"))
    playbooks = load_single_definition(os.path.join(dir, "playbooks.json"))
    plays = load_single_definition(os.path.join(dir, "plays.json"))
    tasks = load_single_definition(os.path.join(dir, "tasks.json"))
    return roles, taskfiles, modules, playbooks, plays, tasks

def load_all_definitions(base_dir):
    dirnames = os.listdir(base_dir)
    loaded = {}
    types = ["roles", "taskfiles", "modules", "playbooks", "plays", "tasks"]
    for dname in dirnames:
        path = os.path.join(base_dir, dname)
        if os.path.isfile(path):
            continue
        def_tuple = load_definitions(path)
        for i, type_key in enumerate(types):
            if type_key not in loaded:
                loaded[type_key] = def_tuple[i]
            else:
                loaded[type_key].merge(def_tuple[i])
    return loaded

def make_dicts(root_definitions, ext_definitions):
    definitions = {
        "roles": ObjectList(),
        "modules": ObjectList(),
        "taskfiles": ObjectList(),
    }
    for type_key in definitions:
        definitions[type_key].merge(root_definitions.get(type_key, ObjectList()))
        definitions[type_key].merge(ext_definitions.get(type_key, ObjectList()))
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
                task.resolved_name = resolve_module(task.executable, dicts.get("modules", {}))
            elif task.executable_type == ExecutableType.ROLE_TYPE:
                task.resolved_name = resolve_role(task.executable, dicts.get("roles", {}), task.collection, task.collections_in_play)
            elif task.executable_type == ExecutableType.TASKFILE_TYPE:
                task.resolved_name = resolve_taskfile(task.executable, dicts.get("taskfiles", {}), task.key)
            if task.resolved_name == "":
                failed = True
    elif isinstance(obj, Play):
        for i in range(len(obj.roles)):
            roleinplay = obj.roles[i]
            if not isinstance(roleinplay, RoleInPlay):
                continue
            roleinplay.resolved_name = resolve_role(roleinplay.name, dicts.get("roles", {}), roleinplay.collection, roleinplay.collections_in_play)
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

def resolve_role(role_name, role_dict={}, my_collection_name="", collections_in_play=[]):
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
    parts = task_key.split(object_delimiter)
    parent_key = ""
    task_defined_path = ""
    for p in parts[::-1]:
        if p.startswith("playbook"+key_delimiter) or p.startswith("taskfile"+key_delimiter):
            task_defined_path = p.split(key_delimiter)[1]
            parent_key = task_key.split(p)[0]
            break
    
    # include/import tasks can have a path like "roles/xxxx/tasks/yyyy.yml"
    # then try to find roles directory
    if taskfile_ref.startswith("roles/"):
        if "roles/" in task_defined_path:
            roles_parent_dir = task_defined_path.split("roles/")[0]
            fpath = os.path.join(roles_parent_dir, taskfile_ref)
            fpath = os.path.normpath(fpath)
            taskfile_key = "{}taskfile{}{}".format(parent_key, key_delimiter, fpath)
            found_tf = taskfile_dict.get(taskfile_key, None)
            if found_tf is not None:
                return found_tf.key

    task_dir = os.path.dirname(task_defined_path)
    fpath = os.path.join(task_dir, taskfile_ref)
    # need to normalize path here because taskfile_ref can be smoething like "../some_taskfile.yml",
    # but "tasks/some_dir/../some_taskfile.yml" cannot be found in the taskfile_dict
    # it will be "tasks/some_taskfile.yml" by this normalize
    fpath = os.path.normpath(fpath)
    taskfile_key = "{}taskfile{}{}".format(parent_key, key_delimiter, fpath)
    found_tf = taskfile_dict.get(taskfile_key, None)
    if found_tf is not None:
        return found_tf.key
    
    return ""

class TreeLoader(object):

    def __init__(self, root, ext, tree, node):

        self.root_dir = root
        self.ext_dir = ext
        self.tree_file = tree
        self.node_file = node

        self.root_definitions = load_all_definitions(self.root_dir)
        self.ext_definitions = load_all_definitions(self.ext_dir)

        self.dicts = make_dicts(self.root_definitions, self.ext_definitions)
        
        debug_task_count = [0, 0]
        tasks = self.root_definitions.get("tasks", ObjectList())
        for i, t in enumerate(tasks.items):
            tasks.items[i], failed = resolve(t, self.dicts)
            debug_task_count[0] += 1
            if failed:
                debug_task_count[1] += 1
        self.root_definitions["tasks"] = tasks

        debug_play_count = [0, 0]
        plays = self.root_definitions.get("plays", ObjectList())
        for i, p in enumerate(plays.items):
            plays.items[i], failed = resolve(p, self.dicts)
            debug_play_count[0] += 1
            if failed:
                debug_play_count[1] += 1
        self.root_definitions["plays"] = plays
        print("DEBUG task resolve count", debug_task_count)
        print("DEBUG play resolve count", debug_play_count)

        

        return

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

    parser.add_argument('-r', '--root', default="", help='path to the input definition dir for root')
    parser.add_argument('-e', '--ext', default="", help='path to the input definition dir for ext')
    parser.add_argument('-t', '--tree', default="", help='path to the output tree file')
    parser.add_argument('-n', '--node', default="array", help='path to the output node objects')
    
    args = parser.parse_args()

    tree_loader = TreeLoader(args.root, args.ext, args.tree, args.node)
    # tree_loader.run()
    sys.exit()

    # TODO: implement

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