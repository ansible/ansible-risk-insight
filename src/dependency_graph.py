import argparse
import os
from struct4 import Repository
from resolver_fqcn import FQCNResolver
from resolver_used_in import UsedInResolver
from resolver_sample_rule import NonBuiltinResolver
from resolver_possible_candidates import PossibleCandidateResolver
from resolver_dependency import DependencyResolver


class DependencyGraph():
    def __init__(self, role_dir="", collection_dir="", output=""):
        self.role_dir = role_dir
        self.collection_dir = collection_dir
        self.output = output

        self.roles = []
        self.collections = []
        self.use_relations = []

    def run(self):

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
            if role_name not in self.roles:
                self.roles.append(role_name)
            rv = self.to_role_variable(role_name)

            dep_roles = role.dependency.get("role", [])
            dep_collections = role.dependency.get("collection", [])

            for dr in dep_roles:
                if dr not in self.roles:
                    self.roles.append(dr)
                drv = self.to_role_variable(dr)
                self.use_relations.append((rv, drv))

            for dc in dep_collections:
                if dc not in self.collections:
                    self.collections.append(dc)
                dcv = self.to_collection_variable(dc)
                self.use_relations.append((rv, dcv))
        
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

    def get_index(self, list_, value):
        for i, item in enumerate(list_):
            if item == value:
                return i
        return None

    def to_role_variable(self, role_name):
        idx = self.get_index(self.roles, role_name)
        if idx is None:
            return None
        return "r{}".format(idx)

    def to_collection_variable(self, collection_name):
        idx = self.get_index(self.collections, collection_name)
        if idx is None:
            return None
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
    parser.add_argument('-o', '--output', default="", help='path to the output json')

    args = parser.parse_args()
    g = DependencyGraph(args.role_dir, args.collection_dir, args.output)
    g.run()


if __name__ == "__main__":
    main()