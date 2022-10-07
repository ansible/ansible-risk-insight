from typing import List
from ..models import RiskAnnotation, TaskCall
from ..risk_annotators.base import RiskType, RISK_ANNOTATION_TYPE
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
            analyzed_data = taskcall.get_annotation_by_type(RISK_ANNOTATION_TYPE)
            for single_ad in analyzed_data:
                if not isinstance(single_ad, RiskAnnotation):
                    continue
                if single_ad.category == RiskType.INBOUND:
                    raw_dst = single_ad.data.get("dest", "")
                    resolved_src = [
                        resolved.get("src", "")
                        for resolved in single_ad.resolved_data
                        if resolved.get("src", "") != ""
                    ]
                    if len(resolved_src) == 0:
                        resolved_src = ""
                    if len(resolved_src) == 1:
                        resolved_src = resolved_src[0]
                    is_mutable_src = single_ad.data.get(
                        "undetermined_src", False
                    )
                    mutable_src_vars = single_ad.data.get(
                        "mutable_src_vars", []
                    )
                    mutable_src_vars = [
                        "{{ " + mv + " }}" for mv in mutable_src_vars
                    ]
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
