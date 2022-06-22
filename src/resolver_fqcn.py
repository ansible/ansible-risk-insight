import re
from struct4 import BuiltinModuleSet
from resolver import Resolver
import logging


module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')
role_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

# set fqcn to all Task and RoleInPlay
class FQCNResolver(Resolver):
    def __init__(self, repo_obj):
        self.repo = repo_obj

    def task(self, obj):
        super().task(obj)
        task = obj
        if task.module == "":
            return
        if task.fqcn == "":
            fqcn = ""
            if task.executable_type == "Module":            
                # if the module name is in fqcn format, just set it
                if module_name_re.match(task.executable):
                    fqcn = task.module
                else:
                    # otherwise, search fqcn from module dict
                    fqcn = self.search_module_fqcn(task.module)
                    if fqcn == "":
                        logging.warning("module \"{}\" not found for task \"{}\"".format(task.module, task.id))
            elif task.executable_type == "Role":
                # if the role name is in fqcn format, just set it
                if role_name_re.match(task.executable):
                    fqcn = task.executable
                else:
                    # otherwise, search fqcn from module dict
                    fqcn = self.search_role_fqcn(task.executable)
                    if fqcn == "":
                        logging.warning("role \"{}\" not found for task \"{}\"".format(task.executable, task.id))
            else:
                if task.executable == "":
                    raise ValueError("the executable type is not set")
                else:
                    raise ValueError("the executable type {} is not supported".format(task.executable))
            task.fqcn = fqcn
        return

    def role_in_play(self, obj):
        super().role_in_play(obj)
        role_in_play = obj
        if role_in_play.fqcn == "":
            fqcn = ""
            if role_name_re.match(role_in_play.name):
                fqcn = role_in_play.name
            else:
                fqcn = self.search_role_fqcn(role_in_play.name)
            role_in_play.fqcn = fqcn
        return

    def search_module_fqcn(self, module_name):
        builtin_modules = BuiltinModuleSet().builtin_modules
        fqcn = ""
        if module_name in builtin_modules:
            fqcn = "ansible.builtin.{}".format(module_name)
        if fqcn == "":
            m = self.repo.get_module_by_short_name(module_name)
            if m is None:
                return ""
            fqcn = m.fqcn
        return fqcn

    def search_role_fqcn(self, role_name):
        r = self.repo.get_role_by_fqcn(role_name)
        if r is not None:
            return r.fqcn
        r = self.repo.get_role_by_short_name(role_name)
        if r is None:
            return ""
        return r.fqcn
