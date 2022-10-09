from typing import List
from ..models import TaskCall
from .base import Rule


class SampleCustomRule(Rule):
    name: str = "SampleCustomRule"
    enabled: bool = False

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        # this sample rule checks if each task has a name
        matched_tasks = []
        message = ""
        # define a condition for this rule here
        for taskcall in taskcalls:
            if taskcall.spec.name == "":
                matched_tasks.append(taskcall)
        message = "{} task(s) don't have the names".format(len(matched_tasks))
        # end of the condition
        matched = len(matched_tasks) > 0
        return matched, matched_tasks, message
