from dataclasses import dataclass

from ansible_risk_insight.models import (
    AnsibleRunContext,
    RunTargetType,
    Rule,
    RuleResult,
    Severity,
)


@dataclass
class SampleRule(Rule):
    # rule definition
    rule_id: str = "Sample101"
    description: str = "echo task block"
    enabled: bool = True
    name: str = "EchoTaskContent"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE

    def match(self, ctx: AnsibleRunContext) -> bool:
        # specify targets to be checked
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        # implement check logic
        task = ctx.current  # get current object of the context

        correct_fqcn = task.get_annotation(key="module.correct_fqcn")
        need_correction = task.get_annotation(key="module.need_correction")

        verdict = True  # indicates the rule is matched or not.
        detail = {}
        task_content = task.content  # get the task content
        task_block = task_content.yaml()  # convert to yaml format by yaml()
        detail["task_block"] = task_block
        # put the data into rule result
        detail["correct_fqcn"] = correct_fqcn
        detail["need_correction"] = need_correction
        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
