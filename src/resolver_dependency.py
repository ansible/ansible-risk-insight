from resolver import Resolver
import re
import logging


module_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')
role_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+$')
role_in_collection_name_re = re.compile(r'^[a-z0-9_]+\.[a-z0-9_]+\.[a-z0-9_]+$')

# set `dependency` attribute to all Role / Collection 
class DependencyResolver(Resolver):
    def __init__(self, repo_obj, include_candidates=True):
        self.repo = repo_obj

    # set `dependency` attribute to Roles
    def role(self, obj):
        role = obj
        # if already set, skip this role
        if len(role.dependency) > 0:
            return

        all_tasks = []
        for tf in role.taskfiles:
            for t in tf.tasks:
                try:
                    tasks = self.repo.get_all_tasks_called_from_one_task(t)
                except:
                    logging.exception("error while getting all tasks called from the task \"{}\", executable: \"{}\"".format(t.id, t.executable))
                    continue
                all_tasks.extend(tasks)
        
        dep_collections = set()
        dep_roles = set()
        for t in all_tasks:
            collection_name, role_name = self.get_dependency_name_from_task(t)
            if collection_name != "" and collection_name not in dep_collections:
                dep_collections.add(collection_name)
            if role_name != "" and role_name not in dep_roles:
                dep_roles.add(role_name)
        dep_collections_list = sorted(list(dep_collections))
        dep_roles_list = sorted(list(dep_roles))
        role.dependency = {
            "collection": dep_collections_list,
            "role": dep_roles_list,
        }
        return

    # set `dependency` attribute to Collections
    def collection(self, obj):
        collection = obj
        # if already set, skip this collection
        if len(collection.dependency) > 0:
            return

        all_tasks = []
        try:
            all_tasks = self.repo.get_all_tasks_called_from_one_collection(collection)
        except:
            logging.exception("error while getting all tasks called in one collection \"{}\"".format(collection.name))
            return
        
        dep_collections = set()
        dep_roles = set()
        for t in all_tasks:
            collection_name, role_name = self.get_dependency_name_from_task(t)
            if collection_name != "" and collection_name not in dep_collections:
                dep_collections.add(collection_name)
            if role_name != "" and role_name not in dep_roles:
                dep_roles.add(role_name)
        dep_collections_list = sorted(list(dep_collections))
        dep_roles_list = sorted(list(dep_roles))
        collection.dependency = {
            "collection": dep_collections_list,
            "role": dep_roles_list,
        }
        return

    def get_dependency_name_from_task(self, task):
        dep_collection_name = ""
        dep_role_name = ""
        if task.executable_type == "Module":
            module_name = task.resolved_name
            if module_name == "" and self.include_candidates and len(task.possible_candidates) > 0:
                module_name = task.possible_candidates[0]
            if module_name_re.match(module_name):
                dep_collection_name = ".".join(module_name.split(".")[:-1])
        elif task.executable_type == "Role":
            role_name = task.resolved_name
            if role_name == "" and self.include_candidates and len(task.possible_candidates) > 0:
                role_name = task.possible_candidates[0]
            if role_name_re.match(role_name):
                dep_role_name = role_name
            elif role_in_collection_name_re.match(role_name):
                dep_collection_name = ".".join(role_name.split(".")[:-1])
        return dep_collection_name, dep_role_name

