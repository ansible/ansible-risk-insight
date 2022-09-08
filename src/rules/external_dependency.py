from rules.base import Rule


class ExternalDependencyRule(Rule):
    name: str = "ExternalDependency"
    enabled: bool = True
    allow_list: list = []
    separate_report: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, tasks: list):
        matched_tasks = []
        message = ""
        external_dependencies = []
        for task in tasks:
            executable_type = task.get("executable_type", "")
            if executable_type != "Module":
                continue
            resolved_name = task.get("resolved_name", "")
            if resolved_name == "":
                continue
            if resolved_name.startswith("ansible.builtin."):
                continue
            if "." not in resolved_name:
                continue
            parts = resolved_name.split(".")
            if len(parts) >= 2:
                collection_name = "{}.{}".format(parts[0], parts[1])
                if collection_name in self.allow_list:
                    continue
                if collection_name not in external_dependencies:
                    external_dependencies.append(collection_name)
                    matched_tasks.append(task)
        external_dependencies = sorted(external_dependencies)
            
        matched = len(external_dependencies) > 0
        message = str(external_dependencies)
        return matched, matched_tasks, message
