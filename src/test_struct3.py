import unittest
from struct3 import Task, Role, Playbook, Repository, config


class TestStruct3(unittest.TestCase):
    """test class of struct3.py
    """
    config.set(collections_path="testdata/installed_collections_path")

    def test_task(self):
        """test method for Task
        """
        test_task_block = '''
        name: Debug Msg
        debug:
          msg: "hello world"
        '''
        t = Task(name="test_task", path="", yaml=test_task_block, parent=None)
        # self.assertEqual(expected, actual)

    def test_role(self):
        """test method for Role
        """
        r = Role(name="test_role", path="testdata/scm_repo/roles/apt", parent=None)
        # self.assertEqual(expected, actual)

    def test_playbook(self):
        """test method for Playbook
        """
        r = Repository(name="test_repository", path="testdata/scm_repo", parent=None, doload=False)
        p = Playbook(name="test_playbook", path="testdata/scm_repo/playbooks/service/nodejs.yml", parent=r)
        # self.assertEqual(expected, actual)

    def test_repository(self):
        """test method for Repository
        """
        r = Repository(name="test_repository", path="testdata/scm_repo", parent=None)
        r.dump()
        # self.assertEqual(expected, actual)

        


if __name__ == "__main__":
    unittest.main()