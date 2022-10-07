from typing import List
from ..models import TaskCall


subject_placeholder = "<SUBJECT>"


class Rule(object):
    name: str = ""
    enabled: bool = False
    separate_report: bool = False
    all_ok_message: str = ""

    def check(self, taskcalls: List[TaskCall], **kwargs):
        raise ValueError("this is a base class method")
