import unittest
from struct4 import Module, Collection, Task, Role, Playbook, Repository, config


class TestStruct3(unittest.TestCase):
    """test class of struct4.py
    """
    config.set(collections_path="testdata/installed_collections_path")

    def test_module(self):
        """test method for Module
        """

        m = Module()
        m.load("testdata/installed_collections_path/ansible_collections/community/general/plugins/modules/files/archive.py")
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
        t.load("testdata/scm_repo/roles/java/tasks/main.yml", 6)
        expected = "dpkg_divert"
        actual = t.module
        self.assertEqual(expected, actual)
        
    def test_role(self):
        """test method for Role
        """
        r = Role()
        r.load("testdata/scm_repo/roles/apt")
        expected = 23
        actual = len(r.tasks)
        self.assertEqual(expected, actual)

    def test_playbook(self):
        """test method for Playbook
        """
        p = Playbook()
        p.load("testdata/scm_repo/playbooks/service/minio.yml")
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
        expected = 22
        actual = len(r.playbooks)
        self.assertEqual(expected, actual)

        expected = 758
        actual = len(r.get_module_dict())
        self.assertEqual(expected, actual)
        
        expected = "testdata/installed_collections_path/ansible_collections/community/general/plugins/modules/files/archive.py"
        m = r.get_module("community.general.archive")
        actual = m.defined_in
        self.assertEqual(expected, actual)
        


if __name__ == "__main__":
    unittest.main()