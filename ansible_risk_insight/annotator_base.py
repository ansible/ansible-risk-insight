from typing import List
from .models import TaskCall, Annotation


class Annotator(object):
    type: str = ""

    def run(self, taskcall: TaskCall) -> List[Annotation]:
        raise ValueError("this is a base class method")
