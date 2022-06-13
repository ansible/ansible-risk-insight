import yaml
import os
import glob

import struct

# class Module:
#     name: str
#     collection_name: str
#     fqcn: str # module_id
#     defined_in: str
#     collection: str
#     category: str
#     used_in: list


class ModuleLoader(object):
    def __init__(self):
        f = open('task_keywords.txt', 'r')
        self.task_keywords = f.read().splitlines()
        f.close()
        f = open('builtin-modules.txt', 'r')
        self.builtin_modules = f.read().splitlines()
        f.close()

    # TODO: fix
    def get_modules_from_role(self, dir):
        modules = []
        # role/library/my_module.py
        target_src =  self.tmp_dir + "/**/library/**/*.py"
        for module_file in glob.glob(target_src, recursive=True):
            module = struct.Module
            mf = module_file.split("/")
            name = mf[-1]
            module_name = name.replace(".py", "")
            module.name = module_name
            module.defined_in = module_file
        return modules
    
    def get_module_from_collection(self, dir):
        # collection
        # - plugins/modules
        modules = []
        target_src = dir + "/**/plugins/**/*.py"
        # print("search file", target_src)
        for col_file in glob.glob(target_src, recursive=True):
            col_path = col_file.replace(dir+"/ansible_collections/", '')
            r = col_path.split("/")
            namespace = r[0]
            name = r[1]
            module_file = r[-1]
            module_name = module_file.replace(".py", "")
            if module_file == "__init__.py":
                continue
            collection = "{0}.{1}".format(namespace, name)
            fqcn = "{0}.{1}.{2}".format(namespace, name, module_name)
            module = struct.Module
            module.name = module_name
            module.fqcn = fqcn
            module.collection = collection
            module.defined_in = col_path
            modules.append(module)
        return modules

    def get_custom_modules(self, library_dir):
        modules = []
        if os.path.exists(library_dir):
            target_src =  library_dir + "/**/*.py"
            for name in glob.glob(target_src, recursive=True):
                r = name.split("/")
                module_file = r[-1]
                module_name = module_file.replace(".py", "")
                module = struct.Module
                module.name = module_name
                module.defined_in = name
                modules.append(module)
        return