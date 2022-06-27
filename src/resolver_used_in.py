from resolver import Resolver


# set used_in to all applicable objects
class UsedInResolver(Resolver):
    def __init__(self, repo_obj):
        self.repo = repo_obj

        self.used_in_dict = {
            "module": {},
            "task": {},
            "taskfile": {},
            "role": {},
        }

    def playbook(self, obj):
        playbook = obj
        # recording used_in info for the roles in this playbook
        for rip in playbook.roles:
            current = self.used_in_dict["role"].get(rip.resolved_name, set())
            current.add(playbook.defined_in)
            self.used_in_dict["role"].update({rip.resolved_name: current})
        return

    def role(self, obj):
        role = obj
        # set used_in for this role
        used_in = self.used_in_dict["role"].get(role.fqcn, set())
        role.used_in = sorted(list(used_in))
        return
    
    def taskfile(self, obj):
        taskfile = obj
        # set used_in for this taskfile
        used_in = self.used_in_dict["taskfile"].get(taskfile.defined_in, set())
        if taskfile.role != "":
            parent_role_used_in = set()
            r = self.repo.get_role_by_short_name(taskfile.role)
            if r is not None:
                parent_role_used_in = self.used_in_dict["role"].get(r.fqcn, set())
            used_in.update(parent_role_used_in)
        taskfile.used_in = sorted(list(used_in))
        

    def task(self, obj):
        task = obj
        # recording used_in info for the executable (Role or Module) in this task
        exec_type = task.executable_type.lower()
        if exec_type == "":
            raise ValueError("the executable type is not set")
        elif exec_type not in self.used_in_dict:
            raise ValueError("the executable type {} is not supported".format(exec_type))
        current = self.used_in_dict[exec_type].get(task.resolved_name, set())
        current.add(task.id)
        self.used_in_dict[exec_type].update({task.resolved_name: current})
        return

    def module(self, obj):
        module = obj
        # set used_in for this module
        used_in = self.used_in_dict["module"].get(module.fqcn, set())
        module.used_in = sorted(list(used_in))


