import re
from struct4 import BuiltinModuleSet
from resolver import Resolver


module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

# set fqcn to all Playbook.tasks and Role.tasks
# set actial Role path to all RoleInPlay.role_path
class FQCNResolver(Resolver):
    def __init__(self, repo_obj):
        self.repo = repo_obj

    def task(self, obj):
        super().task(obj)
        task = obj
        if task.fqcn == "":
            fqcn = ""
            # if the module name is in fqcn format, just set it
            if module_name_re.match(task.module):
                fqcn = task.module
            else:
                # otherwise, search fqcn from module dict
                fqcn = self.search_module_fqcn(task.module)
            task.fqcn = fqcn
        return

    def role_in_play(self, obj):
        super().role_in_play(obj)
        role_in_play = obj
        if role_in_play.role_path == "":
            role_path = self.search_role_path(role_in_play.name)
            role_in_play.role_path = role_path
        return

    def search_module_fqcn(self, module_name):
        builtin_modules = BuiltinModuleSet().builtin_modules
        fqcn = ""
        if module_name in builtin_modules:
            fqcn = "ansible.builtin.{}".format(module_name)
        if fqcn == "":
            module_dict = self.repo.get_module_dict()
            if module_name in module_dict:
                fqcn = module_name
            else:
                for key in module_dict:
                    if key.endswith(".{}".format(module_name)):
                        fqcn = key
                        break
        return fqcn

    def search_role_path(self, role_name):
        role_path = ""
        r = self.repo.get_role_by_name(role_name)
        if r is None:
            return ""
        return r.defined_in
