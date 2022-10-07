from typing import List
from ..models import Task
from .base import Rule


class SampleCustomRule(Rule):
    name: str = "SampleCustomRule"
    enabled: bool = False

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, tasks: List[Task], **kwargs):
        # this sample rule checks if each task has a name
        matched_tasks = []
        message = ""
        # define a condition for this rule here
        for task in tasks:
            if task.name == "":
                matched_tasks.append(task)
        message = "{} task(s) don't have the names".format(len(matched_tasks))
        # end of the condition
        matched = len(matched_tasks) > 0
        return matched, matched_tasks, message
