import argparse
from struct4 import Repository
from resolver_fqcn import FQCNResolver
from resolver_used_in import UsedInResolver
from resolver_sample_rule import NonBuiltinResolver


class SerialResolver():
    def __init__(self, path="", collections_dir="", roles_dir="", output=""):
        self.path = path
        self.collections_dir = collections_dir
        self.roles_dir = roles_dir
        self.output = output

    def run(self):
        repo = Repository()
        repo.load(self.path, self.collections_dir, self.roles_dir)

        # resolve `fqcn` of Task and `role_path` of RoleInPlay
        fqcn_resolver = FQCNResolver(repo_obj=repo)
        repo.resolve(fqcn_resolver)

        # resolve `used_in` of Module / Task / Role
        used_in_resolver = UsedInResolver(repo_obj=repo)
        repo.resolve(used_in_resolver)

        # add `use-non-builtin-module: true` annotation to Task / Role / Playbook if it uses at least one non-builtin module
        non_builtin_resolver = NonBuiltinResolver(repo_obj=repo)
        repo.resolve(non_builtin_resolver)

        if self.output != "":
            # save the resolved repository data as a json file
            json_str = repo.dump()
            with open(self.output, "w") as file:
                file.write(json_str) 


def main():
    parser = argparse.ArgumentParser(
        prog='serial_resolver.py',
        description='Load SCM repo / collections / modules and execute resolvers in a series',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-p', '--repo-path', default="", help='path to SCM repo')
    parser.add_argument('-c', '--installed-collections-path', default="", help='path to directory where collections are installed')
    parser.add_argument('-r', '--installed-roles-path', default="", help='path to directory where roles are installed')
    parser.add_argument('-o', '--output', default="", help='path to the output json')

    args = parser.parse_args()
    r = SerialResolver(args.repo_path, args.installed_collections_path, args.installed_roles_path, args.output)
    r.run()


if __name__ == "__main__":
    main()