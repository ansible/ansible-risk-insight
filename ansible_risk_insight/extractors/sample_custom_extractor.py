from ..models import Task, RiskAnalysisResult
from .base import Extractor


class SampleRiskType:
    NONE = ""
    SAMPLE_RISK_TYPE = "sample"


class SampleCustomExtractor(Extractor):
    name: str = "sample"
    enabled: bool = False

    # whether this task should be analyzed by this or not
    def match(self, task: Task) -> bool:
        # resolved_name = task.resolved_name
        # return resolved_name.startswith("sample.custom.")
        return False

    # extract analyzed_data from task and embed it
    def analyze(self, task: Task) -> Task:
        if not self.match(task):
            return task
        resolved_name = task.resolved_name
        options = task.module_options
        resolved_options = task.resolved_module_options

        analyzed_data = []
        # example of package_install
        if resolved_name == "sample.custom.homebrew":
            res = RiskAnalysisResult(category=SampleRiskType.SAMPLE_RISK_TYPE)
            res.data = self.homebrew(options)
            for ro in resolved_options:
                res.resolved_data.append(self.homebrew(ro))
            analyzed_data.append(res)

        task.analyzed_data = analyzed_data
        return task

    def homebrew(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data
