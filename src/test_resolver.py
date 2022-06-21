import unittest
from struct4 import Repository
from resolver_fqcn import FQCNResolver
from resolver_used_in import UsedInResolver
from resolver_sample_rule import NonBuiltinResolver


class TestResolver(unittest.TestCase):
    """test class of fqcn_resolver.py
    """

    def test_resolver(self):
        """test method for Resolvers
        """
        # initialize Repository
        repo = Repository()
        repo.load("testdata/scm_repo", "testdata/installed_collections_path")
        
        # resolve `fqcn` of Task and `role_path` of RoleInPlay
        fqcn_resolver = FQCNResolver(repo_obj=repo)
        repo.resolve(fqcn_resolver)

        # resolve `used_in` of Module / Task / Role
        used_in_resolver = UsedInResolver(repo_obj=repo)
        repo.resolve(used_in_resolver)

        # add `use-non-builtin-module: true` annotation to Task / Role / Playbook if it uses at least one non-builtin module
        non_builtin_resolver = NonBuiltinResolver(repo_obj=repo)
        repo.resolve(non_builtin_resolver)

        # save the resolved repository data as a json file
        json_str = repo.dump()
        with open("test.json", "w") as file:
            file.write(json_str)
        


if __name__ == "__main__":
    unittest.main()