from struct4 import Module, Collection, Task, TaskFile, Role, RoleInPlay, Playbook, Play, Repository


class Resolver:
    def apply(self, obj):
        obj_type = type(obj).__name__
        if obj_type == "Repository":
            self.repository(obj)
        elif obj_type == "Playbook":
            self.playbook(obj)
        elif obj_type == "Play":
            self.play(obj)
        elif obj_type == "RoleInPlay":
            self.roleinplay(obj)
        elif obj_type == "Role":
            self.role(obj)
        elif obj_type == "TaskFile":
            self.taskfile(obj)
        elif obj_type == "Task":
            self.task(obj)
        elif obj_type == "Collection":
            self.collection(obj)
        elif obj_type == "Module":
            self.module(obj)
        else:
            raise ValueError("{} is not supported".format(obj_type))

    def repository(self, obj):
        if not isinstance(obj, Repository):
            raise ValueError("this object is not a Repository")

    def playbook(self, obj):
        if not isinstance(obj, Playbook):
            raise ValueError("this object is not a Playbook")

    def play(self, obj):
        if not isinstance(obj, Play):
            raise ValueError("this object is not a Play")

    def roleinplay(self, obj):
        if not isinstance(obj, RoleInPlay):
            raise ValueError("this object is not a RoleInPlay")

    def role(self, obj):
        if not isinstance(obj, Role):
            raise ValueError("this object is not a Role")

    def taskfile(self, obj):
        if not isinstance(obj, TaskFile):
            raise ValueError("this object is not a TaskFile")

    def task(self, obj):
        if not isinstance(obj, Task):
            raise ValueError("this object is not a Task")

    def collection(self, obj):
        if not isinstance(obj, Collection):
            raise ValueError("this object is not a Collection")

    def module(self, obj):
        if not isinstance(obj, Module):
            raise ValueError("this object is not a Module")