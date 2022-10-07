from ..models import Task


class Extractor(object):
    name: str = ""
    enabled: bool = False

    def match(self, task: Task) -> bool:
        raise ValueError("this is a base class method")

    def analyze(self, task: Task) -> Task:
        raise ValueError("this is a base class method")
