from typing import List
from ..models import RiskAnnotation, TaskCall
from ..annotators.base import RiskType, RISK_ANNOTATION_TYPE
from .base import Rule


class InboundTransferRule(Rule):
    name: str = "InboundTransfer"
    enabled: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        matched_taskcalls = []
        message = ""
        for taskcall in taskcalls:
            inbound_annos = taskcall.get_annotation_by_type_and_attr(RISK_ANNOTATION_TYPE, "category", RiskType.INBOUND)
            for inbound_data in inbound_annos:
                if not isinstance(inbound_data, RiskAnnotation):
                    continue
                raw_dst = inbound_data.data.get("dest", "")
                resolved_src = [resolved.get("src", "") for resolved in inbound_data.resolved_data if resolved.get("src", "") != ""]
                if len(resolved_src) == 0:
                    resolved_src = ""
                if len(resolved_src) == 1:
                    resolved_src = resolved_src[0]
                is_mutable_src = inbound_data.data.get("undetermined_src", False)
                mutable_src_vars = inbound_data.data.get("mutable_src_vars", [])
                mutable_src_vars = ["{{ " + mv + " }}" for mv in mutable_src_vars]
                if len(mutable_src_vars) == 0:
                    mutable_src_vars = ""
                if len(mutable_src_vars) == 1:
                    mutable_src_vars = mutable_src_vars[0]
                if is_mutable_src:
                    matched_taskcalls.append(taskcall)
                    message += "- From: {}\n".format(mutable_src_vars)
                    # message += "      (default value: {})\n".format(
                    #     resolved_src
                    # )
                    message += "  To: {}\n".format(raw_dst)
        matched = len(matched_taskcalls) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_taskcalls, message
