from resolver import Resolver
import logging


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

        if task.executable_type == "Module":
            m = self.repo.get_module_by_fqcn(task.resolved_name)
            if m is None:
                return
            if not m.builtin:
                task.annotations[self.annotation_name] = True
        elif task.executable_type == "Role":
            r = self.repo.get_role_by_fqcn(task.resolved_name)
            if r is None:
                return
            use_non_builtin = False
            all_modules_in_the_task = []
            try:
                all_modules_in_the_task = self.repo.get_all_modules_in_task(task)
            except:
                logging.exception("error while getting all modules in the task \"{}\", executable: \"{}\"".format(task.id, task.executable))
            for m in all_modules_in_the_task:
                if m is None:
                    continue
                if not m.builtin:
                    use_non_builtin = True
                    break
            if use_non_builtin:
                task.annotations[self.annotation_name] = True
        return

    def taskfile(self, obj):
        taskfile = obj
        # if the annotation is already set, do nothing
        if taskfile.annotations.get(self.annotation_name, False):
            return
        
        use_non_builtin = False
        for t in taskfile.tasks:
            if t.annotations.get(self.annotation_name, False):
                use_non_builtin = True
                break
        if use_non_builtin:
            taskfile.annotations[self.annotation_name] = True

    # add `use-non-builtin-module` annotation to the role if it uses a task with the annotation
    def role(self, obj):
        role = obj
        # if the annotation is already set, do nothing
        if role.annotations.get(self.annotation_name, False):
            return
        
        use_non_builtin = False
        for tf in role.taskfiles:
            if tf.annotations.get(self.annotation_name, False):
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
                if r_in_play.resolved_name == "":
                    continue
                r = self.repo.get_role_by_fqcn(r_in_play.resolved_name)
                if r is None:
                    logging.warning("role \"{}\" not found for playbook \"{}\"".format(r_in_play.resolved_name, playbook.defined_in))
                    continue
                if r.annotations.get(self.annotation_name, False):
                    use_non_builtin = True
                    break
        if use_non_builtin:
            playbook.annotations[self.annotation_name] = True

    # add `use-non-builtin-module` annotation to the collection if it uses a playbook/role with the annotation
    def collection(self, obj):
        collection = obj
        # if the annotation is already set, do nothing
        if collection.annotations.get(self.annotation_name, False):
            return

        use_non_builtin = False
        for p in collection.playbooks:
            if p.annotations.get(self.annotation_name, False):
                use_non_builtin = True
                break
        if not use_non_builtin:
            for r in collection.roles:
                if r.annotations.get(self.annotation_name, False):
                    use_non_builtin = True
                    break
        if use_non_builtin:
            collection.annotations[self.annotation_name] = True


