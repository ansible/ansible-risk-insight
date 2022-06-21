from resolver import Resolver


# set used_in to all applicable objects
class UsedInResolver(Resolver):
    def __init__(self, repo_obj):
        self.repo = repo_obj

        self.used_in_dict = {
            "module": {},
            "task": {},
            "role": {},
        }

    def playbook(self, obj):
        playbook = obj
        # storing used_in info for the tasks in this playbook
        for t in playbook.tasks:
            current = self.used_in_dict["task"].get(t.id, set())
            current.add(playbook.defined_in)
            self.used_in_dict["task"].update({t.id: current})

        # storing used_in info for the roles in this playbook
        for r in playbook.roles:
            current = self.used_in_dict["role"].get(r.role_path, set())
            current.add(playbook.defined_in)
            self.used_in_dict["role"].update({r.role_path: current})
        return

    def role(self, obj):
        role = obj
        # storing used_in info for the tasks in this role
        for t in role.tasks:
            current = self.used_in_dict["task"].get(t.id, set())
            current.add(role.defined_in)
            self.used_in_dict["task"].update({t.id: current})

        # set used_in for this role
        used_in = self.used_in_dict["role"].get(role.defined_in, set())
        role.used_in = sorted(list(used_in))
        return

    def task(self, obj):
        task = obj
        # storing used_in info for the module in this task
        current = self.used_in_dict["module"].get(task.fqcn, set())
        current.add(task.id)
        self.used_in_dict["module"].update({task.fqcn: current})

        # set used_in for this task
        used_in = self.used_in_dict["task"].get(task.id, set())
        task.used_in = sorted(list(used_in))
        return

    def module(self, obj):
        module = obj
        # set used_in for this module
        used_in = self.used_in_dict["module"].get(module.fqcn, set())
        module.used_in = sorted(list(used_in))


