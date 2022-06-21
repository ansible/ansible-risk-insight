from struct4 import Module, Collection, Task, Role, Playbook, Repository, BuiltinModuleSet, config
from resolver import Resolver


# set `use-non-builtin-module` annotation to all Tasks / Roles / Playbooks that invoke non-builtin module
class NonBuiltinResolver(Resolver):
    def __init__(self, repo_obj):
        self.repo = repo_obj

        self.annotation_name = "use-non-builtin-module"

    # add `use-non-builtin-module` annotation to the task if it uses non-builtin module
    def task(self, obj):
        task = obj
        # if the annotation is already set, do nothing
        if task.annotations.get(self.annotation_name, False):
            return

        m = self.repo.get_module_by_fqcn(task.fqcn)
        if m is None:
            return
        if not m.builtin:
            task.annotations[self.annotation_name] = True
        return

    # add `use-non-builtin-module` annotation to the role if it uses a task with the annotation
    def role(self, obj):
        role = obj
        # if the annotation is already set, do nothing
        if role.annotations.get(self.annotation_name, False):
            return
        
        use_non_builtin = False
        for t in role.tasks:
            if t.annotations.get(self.annotation_name, False):
                use_non_builtin = True
                break
        if use_non_builtin:
            role.annotations[self.annotation_name] = True

    # add `use-non-builtin-module` annotation to the playbook if it uses a role/task with the annotation
    def playbook(self, obj):
        playbook = obj
        # if the annotation is already set, do nothing
        if playbook.annotations.get(self.annotation_name, False):
            return

        use_non_builtin = False
        for t in playbook.tasks:
            if t.annotations.get(self.annotation_name, False):
                use_non_builtin = True
                break
        if not use_non_builtin:
            for r_in_play in playbook.roles:
                r = self.repo.get_role_by_name(r_in_play.name)
                if r.annotations.get(self.annotation_name, False):
                    use_non_builtin = True
                    break
        if use_non_builtin:
            playbook.annotations[self.annotation_name] = True


