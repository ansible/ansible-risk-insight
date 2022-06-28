import unittest
from struct4 import Module, Collection, Task, Role, Playbook, Repository


class TestStruct4(unittest.TestCase):
    """test class of struct4.py
    """

    def test_module(self):
        """test method for Module
        """

        m = Module()
        m.load("testdata/installed_collections_path/ansible_collections/community/general/plugins/modules/files/archive.py", collection_name="community.general")
        expected = "community.general.archive"
        actual = m.fqcn
        self.assertEqual(expected, actual)

    def test_collection(self):
        """test method for Collection
        """

        c = Collection()
        c.load("testdata/installed_collections_path/ansible_collections/community/general")
        expected = 545
        actual = len(c.modules)
        self.assertEqual(expected, actual)
    
    def test_task(self):
        """test method for Task
        """
        t = Task()
        task_block_dict = {
            "name": "Divert default Java security policy configuration file",
            "dpkg_divert": {
                "path": '{{ java__security_policy_path }}',
                "state": 'present',
            },
        }
        t.load("testdata/scm_repo/ansible/roles/java/tasks/main.yml", 6, task_block_dict)
        expected = "dpkg_divert"
        actual = t.module
        self.assertEqual(expected, actual)
        
    def test_role(self):
        """test method for Role
        """
        r = Role()
        r.load("testdata/scm_repo/ansible/roles/apt")
        expected = 1
        actual = len(r.taskfiles)
        self.assertEqual(expected, actual)

        tasks = []
        for tf in r.taskfiles:
            tasks.extend(tf.tasks)
        expected = 23
        actual = len(tasks)
        self.assertEqual(expected, actual)

    def test_playbook(self):
        """test method for Playbook
        """
        p = Playbook()
        p.load("testdata/scm_repo/ansible/playbooks/service/minio.yml")
        expected = 2
        actual = len(p.tasks)
        self.assertEqual(expected, actual)

        expected = 11
        actual = len(p.roles)
        self.assertEqual(expected, actual)

    def test_repository(self):
        """test method for Repository
        """
        r = Repository()
        r.load("testdata/scm_repo", "testdata/installed_collections_path")
        expected = 360
        actual = len(r.playbooks)
        self.assertEqual(expected, actual)

        expected = 762
        actual = len(r.module_dict)
        self.assertEqual(expected, actual)
        
        expected = "installed_collections_path/ansible_collections/community/general/plugins/modules/files/archive.py"
        m = r.get_module_by_fqcn("community.general.archive")
        actual = m.defined_in
        self.assertEqual(expected, actual)

        data = r.dump()
        with open("test.json", "w") as file:
            file.write(data)
        
        data_str = ""
        with open("test.json", "r") as file:
            data_str = file.read()
        r2 = Repository()
        r2.from_json(data_str)

        expected = 762
        actual = len(r2.module_dict)
        self.assertEqual(expected, actual)


    # testdata2
    def test_repository_2(self):
        """test method for Repository
        """
        r = Repository()
        r.load("testdata2/scm_repo", "testdata2/installed_collections_path", "testdata2/installed_roles_path")

        expected = 943
        actual = len(r.module_dict)
        self.assertEqual(expected, actual)

        expected = 91
        actual = len(r.role_dict)
        self.assertEqual(expected, actual)

        data = r.dump()
        with open("test2.json", "w") as file:
            file.write(data)

    # testdata3
    def test_repository_3(self):
        """test method for Repository
        """
        r = Repository()
        r.load("testdata3/scm_repo", "testdata3/installed_collections_path")


if __name__ == "__main__":
    unittest.main()