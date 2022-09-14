class Extractor(object):
    name: str = ""
    enabled: bool = False

    def match(self, task: dict) -> bool:
        raise ValueError("this is a base class method")

    def analyze(self, task: dict) -> dict:
        raise ValueError("this is a base class method")
