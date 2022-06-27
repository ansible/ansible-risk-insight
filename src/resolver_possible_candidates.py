from struct4 import Module, Role
from resolver import Resolver
import logging
import json


# set `possible_candidates` attribute to all Tasks / RoleInPlay 
class PossibleCandidateResolver(Resolver):
    def __init__(self, repo_obj):
        self.repo = repo_obj


        self.popular_module_dict = {}
        data = []
        with open("popular_module_dict.json", "r") as file:
            data = json.load(file)

        for m_dict in data.values():
            m_json = json.dumps(m_dict)
            m = Module()
            m.from_json(m_json)
            self.popular_module_dict[m.fqcn] = m

        self.popular_role_dict = {}
        data = []
        with open("popular_role_dict.json", "r") as file:
            data = json.load(file)

        for r_dict in data.values():
            r_json = json.dumps(r_dict)
            r = Role()
            r.from_json(r_json)
            self.popular_role_dict[r.fqcn] = r

    # set `possible_candidates` attribute to Tasks that have empty `resolved_name` attribute
    def task(self, obj):
        task = obj
        # if the resolved_name is not empty, do nothing
        if task.resolved_name != "":
            return

        # if the possible_candidates are already set, do nothing
        if len(task.possible_candidates) > 0:
            return

        candidates = []
        if task.executable_type == "Module":
            candidates = self.find_candidate_modules_by_short_name(task.module)
        elif task.executable_type == "Role":
            candidates = self.find_candidate_roles_by_short_name(task.executable)
        task.possible_candidates = candidates
        return

    def find_candidate_modules_by_short_name(self, short_name):
        candidates = []
        for v in self.popular_module_dict.values():
            if v.name == short_name:
                candidates.append(v.fqcn)
        return candidates

    def find_candidate_roles_by_short_name(self, short_name):
        candidates = []
        for v in self.popular_role_dict.values():
            if v.name == short_name:
                candidates.append(v.fqcn)
        return candidates


