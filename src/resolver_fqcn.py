import re
from struct4 import Module, Collection, Task, Role, Playbook, Repository, BuiltinModuleSet, config


module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

# set fqcn to all Playbook.tasks and Role.tasks
# set actial Role path to all RoleInPlay.role_path in Playbook.roles
class FQCNResolver:
    def __init__(self, repo_path, collections_path):
        r = Repository()
        r.load(repo_path, collections_path)
        self.repo = r
        self.module_dict = self.repo.get_module_dict()
        self.role_dict = self.repo.get_role_dict()

    def resolve(self):
        self.resolve_module()
    
    def resolve_module(self):
        # Repository.playbooks
        for i, p in enumerate(self.repo.playbooks):
            for j, t in enumerate(p.tasks):
                updated_task = self.embed_module_fqcn(t)
                self.set_module_used_in(updated_task.fqcn, updated_task.defined_in)
                self.repo.playbooks[i].tasks[j] = updated_task
        # Repository.roles
        for i, r in enumerate(self.repo.roles):
            for j, t in enumerate(r.tasks):
                updated_task = self.embed_module_fqcn(t)
                self.set_module_used_in(updated_task.fqcn, updated_task.defined_in)
                self.repo.roles[i].tasks[j] = updated_task

    def resolve_role(self):
        for i, p in enumerate(self.repo.playbooks):
            for j, r in enumerate(p.roles):
                updated_role_in_play = self.embed_role_path(r)
                self.set_role_used_in(updated_role_in_play.name, updated_role_in_play.defined_in)
                self.repo.playbooks[i].roles[j] = updated_role_in_play
                

    def embed_module_fqcn(self, task):
        updated_task = task
        if task.fqcn != "":
            return task
        
        builtin_modules = BuiltinModuleSet().builtin_modules
        fqcn = ""
        if module_name_re.match(task.module):
            fqcn = task.module
        if fqcn == "":
            if task.module in builtin_modules:
                fqcn = "ansible.builtin.{}".format(task.module)
        if fqcn == "":
            for key in self.module_dict:
                if key.endswith(".{}".format(task.module)):
                    fqcn = key
                    break
        updated_task.fqcn = fqcn
        return updated_task

    def embed_role_path(self, role_in_play):
        updated_role_in_play = role_in_play
        if role_in_play.role_path != "":
            return role_in_play

        role_path = ""
        if role_in_play.name in self.role_dict:
            r = self.role_dict[role_in_play.name]
            role_path = r.defined_in
        updated_role_in_play.role_path = role_path
        return updated_role_in_play

    def set_module_used_in(self, module_fqcn, fpath):
        for i, c in enumerate(self.repo.collections):
            if not module_fqcn.startswith(c.name):
                continue
            for j, m in enumerate(c.modules):
                if m.fqcn == module_fqcn:
                    self.repo.collections[i].modules[j].used_in.append(fpath)
                    return
        return

    def set_role_used_in(self, role_name, fpath):
        for i, r in enumerate(self.repo.roles):
            if r.name == role_name:
                self.repo.roles[i].used_in.append(fpath)
                return
        return



def main():
    r = FQCNResolver("testdata/scm_repo", "testdata/installed_collections_path")
    r.resolve()

if __name__ == "__main__":
    main()