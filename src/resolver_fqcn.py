import os
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
            elif task.executable_type == "TaskFile":
                # if the role name is in fqcn format, just set it
                if role_name_re.match(task.executable):
                    fqcn = task.executable
                else:
                    # otherwise, search fqcn from module dict
                    fqcn = self.search_taskfile_path(task.defined_in, task.executable)
                    if fqcn == "":
                        # if "{{" is found in the target path for include_tasks/import_tasks, 
                        # task file reference is parameterized, so give up to get fqcn in the case.
                        if "{{" in task.executable:
                            logging.debug("task file \"{}\" is including variable and we cannot resolve this for the task \"{}\"".format(task.executable, task.id))
                            pass
                        else:
                            # otherwise, the path should be resolved but not found. warn it here.
                            logging.warning("task file \"{}\" not found for task \"{}\"".format(task.executable, task.id))
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

    def roleinplay(self, obj):
        super().roleinplay(obj)
        roleinplay = obj
        if roleinplay.fqcn == "":
            fqcn = ""
            if role_name_re.match(roleinplay.name):
                fqcn = roleinplay.name
            else:
                fqcn = self.search_role_fqcn(roleinplay.name)
            roleinplay.fqcn = fqcn
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

    def search_taskfile_path(self, task_defined_path, taskfile_ref):
        # include/import tasks can have a path like "roles/xxxx/tasks/yyyy.yml"
        # then try to find roles directory
        if taskfile_ref.startswith("roles/"):
            if "/roles/" in task_defined_path:
                roles_parent_dir = task_defined_path.split("/roles/")[0]
                fpath = os.path.join(roles_parent_dir, taskfile_ref)
                fpath = os.path.normpath(fpath)
                tf = self.repo.get_taskfile_by_path(fpath)
                if tf is not None:
                    return tf.defined_in

        task_dir = os.path.dirname(task_defined_path)
        fpath = os.path.join(task_dir, taskfile_ref)
        # need to normalize path here because taskfile_ref can be smoething like "../some_taskfile.yml",
        # but "tasks/some_dir/../some_taskfile.yml" cannot be found in the taskfile_dict
        # it will be "tasks/some_taskfile.yml" by this normalize
        fpath = os.path.normpath(fpath)
        tf = self.repo.get_taskfile_by_path(fpath)
        if tf is None:
            return ""
        fqcn = tf.defined_in
        return fqcn

    def search_role_fqcn(self, role_name):
        r = self.repo.get_role_by_fqcn(role_name)
        if r is not None:
            return r.fqcn
        r = self.repo.get_role_by_short_name(role_name)
        if r is not None:
            return r.fqcn
        return ""
