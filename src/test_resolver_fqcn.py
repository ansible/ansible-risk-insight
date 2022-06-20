import unittest
from resolver_fqcn import FQCNResolver


class TestFQCNResolver(unittest.TestCase):
    """test class of fqcn_resolver.py
    """

    def test_resolver(self):
        """test method for Module
        """

        r = FQCNResolver("testdata/scm_repo", "testdata/installed_collections_path")
        r.resolve()

        all_modules = [v for v in r.repo.get_module_dict().values()]
        top_used_modules = sorted(all_modules, key=lambda x: len(x.used_in), reverse=True)
        top_5_most_used_modules = top_used_modules[:5]
        top_used_non_builtin_modules = [m for m in top_used_modules if not m.builtin]
        top_3_most_used_non_builtin_modules = top_used_non_builtin_modules[:3]


        expected = [
            "ansible.builtin.file",
            "ansible.builtin.template",
            "ansible.builtin.import_role",
            "ansible.builtin.command",
            "ansible.builtin.meta",
        ]
        print("-----------------------------------------------")
        print("Top 5 most used modules (including builtin)")
        print("-----------------------------------------------")
        for i, m in enumerate(top_5_most_used_modules):
            print("FQCN:", m.fqcn)
            print("# of used_in:", len(m.used_in))
            print()
            actual = m.fqcn
            self.assertEqual(expected[i], actual)


        expected = [
            "community.general.dpkg_divert",
            "community.mysql.mysql_db",
            "ansible.posix.mount"
        ]
        print("-----------------------------------------------")
        print("Top 3 most used modules (except builtin)")
        print("-----------------------------------------------")
        for i, m in enumerate(top_3_most_used_non_builtin_modules):
            print("FQCN:", m.fqcn)
            print("# of used_in:", len(m.used_in))
            print()
            actual = m.fqcn
            self.assertEqual(expected[i], actual)
       
    

        


if __name__ == "__main__":
    unittest.main()