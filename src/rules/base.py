class Rule(object):
    name: str = ""
    enabled: bool = False
    separate_report: bool = False

    def check(self, tasks: list):
        raise ValueError("this is a base class method")
