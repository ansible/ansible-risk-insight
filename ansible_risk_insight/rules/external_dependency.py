from typing import List
from ..models import ExecutableType, Task
from .base import Rule, subject_placeholder


class ExternalDependencyRule(Rule):
    name: str = "ExternalDependency"
    enabled: bool = True
    allow_list: list = []
    separate_report: bool = True
    all_ok_message = "No {} depend on external dependencies".format(
        subject_placeholder
    )

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, tasks: List[Task], **kwargs):
        collection_name = kwargs.get("collection_name", "")
        if collection_name != "":
            self.allow_list.append(collection_name)
        allow_list = kwargs.get("allow_list", [])
        if len(allow_list) > 0:
            self.allow_list.extend(allow_list)
        matched_tasks = []
        message = ""
        external_dependencies = []
        for task in tasks:
            executable_type = task.executable_type
            if executable_type != ExecutableType.MODULE_TYPE:
                continue
            resolved_name = task.resolved_name
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
