from typing import List
from ..models import Task


subject_placeholder = "<SUBJECT>"


class Rule(object):
    name: str = ""
    enabled: bool = False
    separate_report: bool = False
    all_ok_message: str = ""

    def check(self, tasks: List[Task], **kwargs):
        raise ValueError("this is a base class method")
