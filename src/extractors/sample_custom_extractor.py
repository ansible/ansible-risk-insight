from extractors.base import Extractor


class SampleCustomExtractor(Extractor):
    name: str = "sample"
    enabled: bool = False

    # whether this task should be analyzed by this or not
    def match(self, task: dict) -> bool:
        # resolved_name = task.get("resolved_name", "")
        # return resolved_name.startswith("sample.custom.")
        return False

    # extract analyzed_data from task and embed it
    def analyze(self, task: dict) -> dict:
        if not self.match(task):
            return task
        resolved_name = task.get("resolved_name", "")
        options = task.get("module_options", {})
        resolved_options = task.get("resolved_module_options", {})

        analyzed_data = []
        # example of package_install
        if resolved_name == "sample.custom.homebrew":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.homebrew(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.homebrew(ro))
            analyzed_data.append(res)

        task["analyzed_data"] = analyzed_data

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
