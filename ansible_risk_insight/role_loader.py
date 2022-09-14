import yaml
import os
import glob

import struct
import task_loader
import module_loader

# class Role:
#     name: str
#     defined_in: str # role_id
#     source: str # collection/scm repo/galaxy
#     tasks: list
#     modules: list


class RoleLoader(object):
    def __init__(self):
        f = open('task_keywords.txt', 'r')
        self.task_keywords = f.read().splitlines()
        f.close()
        f = open('builtin-modules.txt', 'r')
        self.builtin_modules = f.read().splitlines()
        f.close()

    def load_role(self, dir):
        role_repos = []
        # tmp/role_name/tasks
        # roles/
        #     common/
        #         tasks/
        # role dirを取得
        # 各role dir内のtask
        files = os.listdir(dir)
        role_dir = [f for f in files if os.path.isdir(os.path.join(dir, f))]
        for role in role_dir:
            rr = struct.RoleRepo()
            rr.name = role
            tloader = task_loader.TaskLoader()
            rr.tasks = tloader.get_tasks_from_role(role)
            mloader = module_loader.ModuleLoader() 
            rr.modules = mloader.get_modules_from_role(role)
            role_repos.append(rr)
        return role_repos
    