from dataclasses import dataclass, field
import argparse
import os
import json
from struct4 import Repository, Role, Collection, JSONSerializable


@dataclass
class Relation(JSONSerializable):
    subject: object
    target: object

@dataclass
class Dependency(JSONSerializable):
    src: object
    dst: object
    relations: list = field(default_factory=list)

    def set_relations(self, repo, all_task_dict):
        if repo is None:
            raise ValueError("repo is required to set relations")

        relations = []
        tasks = self.get_tasks(repo, self.src, all_task_dict)
        for t in tasks:
            if t.executable_type not in ["Module", "Role"]:
                continue
            resolved_name = ""
            if t.resolved_name == "":
                if len(t.possible_candidates) > 0:
                    resolved_name = t.possible_candidates[0]
                else:
                    continue
            used = False
            target = None
            if t.executable_type == "Module":
                m = repo.get_module_by_fqcn(resolved_name)
                if m is None:
                    continue
                if isinstance(self.dst, Role) and m.role == self.dst.name:
                    used = True
                    target = m
                elif isinstance(self.dst, Collection) and m.collection == self.dst.name:
                    used = True
                    target = m
            elif t.executable_type == "Role":
                r = repo.get_role_by_fqcn(resolved_name)
                if r is None:
                    continue
                if isinstance(self.dst, Role) and r.name == self.dst.name:
                    used = True
                    target = r
                elif isinstance(self.dst, Collection) and r.collection == self.dst.name:
                    used = True
                    target = r
            if used and target is not None:
                rl = Relation(subject=t, target=target)
                relations.append(rl)
        self.relations = relations
    
    def get_tasks(self, repo, obj, all_task_dict):
        tasks = []
        if isinstance(obj, Role):
            key = "Role:{}".format(obj.name)
            if key in all_task_dict:
                tasks = all_task_dict.get(key, [])
            else:
                tasks = repo.get_all_tasks_called_from_one_role(obj)
                all_task_dict[key] = tasks
        elif isinstance(obj, Collection):
            key = "Collection:{}".format(obj.name)
            if key in all_task_dict:
                tasks = all_task_dict.get(key, [])
            else:
                tasks = repo.get_all_tasks_called_from_one_collection(obj)
                all_task_dict[key] = tasks
        return tasks


class DependencyGraph():
    def __init__(self, role_dir="", collection_dir="", all_in_one_file="", output=""):
        self.role_dir = role_dir
        self.collection_dir = collection_dir
        self.all_in_one_file = all_in_one_file
        self.output = output

        self.roles = []
        self.collections = []
        self.use_relations = []
        self.all_task_dict = {}

        self.dependency_map = {}

    def run(self):

        if self.all_in_one_file == "":
            self.load_files_from_dir()
            self.save(mapjson=True, neo4j=True)
        else:
            self.load_all_in_one_file()
            self.save(mapjson=True)

    def load_all_in_one_file(self):
        repo = Repository()
        json_str = ""
        with open(self.all_in_one_file, "r") as file:
            json_str = file.read()
        repo.from_json(json_str)
        for i, r in enumerate(repo.installed_roles):
            role_map_key = "Role:{}".format(r.name)
            print("[{}/{}] {}".format(i+1, len(repo.installed_roles), role_map_key))
            dep_map_for_the_role = {}
            dep_roles = r.dependency.get("role", [])
            for dr_name in dep_roles:
                dr = self.get_obj(repo, "role", dr_name)
                if dr is None:
                    continue
                dep_role_map_key = "Role:{}".format(dr.name)
                d = Dependency(src=r, dst=dr)
                d.set_relations(repo, self.all_task_dict)
                dep_map_for_the_role[dep_role_map_key] = d
            dep_colls = r.dependency.get("collection", [])
            for dc_name in dep_colls:
                dc = self.get_obj(repo, "collection", dc_name)
                if dc is None:
                    continue
                dep_coll_map_key = "Collection:{}".format(dc.name)
                d = Dependency(src=r, dst=dc)
                d.set_relations(repo, self.all_task_dict)
                dep_map_for_the_role[dep_coll_map_key] = d
            if len(dep_map_for_the_role) > 0:
                self.dependency_map[role_map_key] = dep_map_for_the_role
        for i, c in enumerate(repo.installed_collections):
            coll_map_key = "Collection:{}".format(c.name)
            print("[{}/{}] {}".format(i+1, len(repo.installed_collections), coll_map_key))
            dep_map_for_the_coll = {}
            dep_roles = c.dependency.get("role", [])
            for dr_name in dep_roles:
                dr = self.get_obj(repo, "role", dr_name)
                if dr is None:
                    continue
                dep_role_map_key = "Role:{}".format(dr.name)
                d = Dependency(src=c, dst=dr)
                d.set_relations(repo, self.all_task_dict)
                dep_map_for_the_coll[dep_role_map_key] = d
            dep_colls = c.dependency.get("collection", [])
            for dc_name in dep_colls:
                dc = self.get_obj(repo, "collection", dc_name)
                if dc is None:
                    continue
                dep_coll_map_key = "Collection:{}".format(dc.name)
                d = Dependency(src=c, dst=dc)
                d.set_relations(repo, self.all_task_dict)
                dep_map_for_the_coll[dep_coll_map_key] = d
            if len(dep_map_for_the_coll) > 0:
                self.dependency_map[coll_map_key] = dep_map_for_the_coll

    def load_files_from_dir(self):
        files = os.listdir(self.role_dir)
        for fname in files:
            fpath = os.path.join(self.role_dir, fname)
            json_str = ""
            with open(fpath, "r") as file:
                json_str = file.read()
            repo = Repository()
            repo.from_json(json_str)

            role = None
            for r in repo.installed_roles:
                if r.name.replace(".", "-") == fname.replace(".json", ""):
                    role = r
                    break
            if role is None:
                continue

            role_name = role.name
            rv = self.to_role_variable(role_name)

            dep_roles = role.dependency.get("role", [])
            dep_collections = role.dependency.get("collection", [])

            role_map_key = "Role:{}".format(role_name)
            self.dependency_map[role_map_key] = []

            for dr in dep_roles:
                drv = self.to_role_variable(dr)
                self.use_relations.append((rv, drv))
                self.dependency_map[role_map_key].append("Role:{}".format(dr))

            for dc in dep_collections:
                if dc == "ansible.builtin":
                    continue
                dcv = self.to_collection_variable(dc)
                self.use_relations.append((rv, dcv))
                self.dependency_map[role_map_key].append("Collection:{}".format(dc))

        files = os.listdir(self.collection_dir)
        for fname in files:
            fpath = os.path.join(self.collection_dir, fname)
            json_str = ""
            with open(fpath, "r") as file:
                json_str = file.read()
            repo = Repository()
            repo.from_json(json_str)

            for c in repo.installed_collections:
                if c.name.endswith("GALAXY.yml"):
                    continue
                if c.name == "ansible.builtin":
                    continue
            
                cv = self.to_collection_variable(c.name)

                dep_roles = c.dependency.get("role", [])
                dep_collections = c.dependency.get("collection", [])


                collection_map_key = "Collection:{}".format(c.name)
                self.dependency_map[collection_map_key] = []

                for dr in dep_roles:
                    drv = self.to_role_variable(dr)
                    self.use_relations.append((cv, drv))
                    self.dependency_map[collection_map_key].append("Role:{}".format(dr))

                for dc in dep_collections:
                    if dc == "ansible.builtin":
                        continue
                    dcv = self.to_collection_variable(dc)
                    self.use_relations.append((cv, dcv))
                    self.dependency_map[collection_map_key].append("Collection:{}".format(dc))

    def save(self, mapjson=False, neo4j=False):
        
        if mapjson:
            dep_map_json = json.dumps(self.dependency_map)
            with open("dependency_map.json", "w") as file:
                pass
                # file.write(dep_map_json)
        
        if neo4j:
            lines = ""
            for r in self.roles:
                rv = self.to_role_variable(r)
                lines += "CREATE({}:Role{{name:\"{}\"}})\n".format(rv, r)

            for c in self.collections:
                cv = self.to_collection_variable(c)
                lines += "CREATE({}:Collection{{name:\"{}\"}})\n".format(cv, c)

            for i, (s, d) in enumerate(self.use_relations):
                lines += "CREATE({})-[u{}:use]->({})\n".format(s, i, d)
            
            lines += "RETURN *"

            if self.output != "":
                with open(self.output, "w") as file:
                    file.write(lines)

    def get_obj(self, repo, type_, name):
        if type_ == "collection":
            for c in repo.installed_collections:
                if c.name == name:
                    return c
        elif type_ == "role":
            for r in repo.installed_roles:
                if r.name == name:
                    return r
        return None

    def get_index(self, list_, value):
        for i, item in enumerate(list_):
            if item == value:
                return i
        return None

    def to_role_variable(self, role_name):
        idx = self.get_index(self.roles, role_name)
        if idx is None:
            self.roles.append(role_name)
            idx = len(self.roles) - 1
        return "r{}".format(idx)

    def to_collection_variable(self, collection_name):
        idx = self.get_index(self.collections, collection_name)
        if idx is None:
            self.collections.append(collection_name)
            idx = len(self.collections) - 1
        return "c{}".format(idx)


def main():
    parser = argparse.ArgumentParser(
        prog='dependency_graph.py',
        description='make Neo4j cypher query to show dependency graph',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-r', '--role-dir', default="", help='path to role result directory')
    parser.add_argument('-c', '--collection-dir', default="", help='path to collection result directory')
    parser.add_argument('-a', '--all-in-one-file', default="", help='path to all in one file with all roles/collections')
    parser.add_argument('-o', '--output', default="", help='path to the output json')

    args = parser.parse_args()
    g = DependencyGraph(args.role_dir, args.collection_dir, args.all_in_one_file, args.output)
    g.run()


if __name__ == "__main__":
    main()