from typing import List
from ..models import RiskAnnotation, TaskCall
from ..risk_annotators.base import RiskType, RISK_ANNOTATION_TYPE
from .base import Rule


class OutboundTransferRule(Rule):
    name: str = "OutboundTransfer"
    enabled: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, taskcalls: List[TaskCall], **kwargs):
        matched_taskcalls = []
        message = ""
        for taskcall in taskcalls:
            outbound_annos = taskcall.get_annotation_by_type_and_attr(RISK_ANNOTATION_TYPE, "category", RiskType.OUTBOUND)
            for outbound_data in outbound_annos:
                if not isinstance(outbound_data, RiskAnnotation):
                    continue
                raw_src = outbound_data.data.get("src", "")
                resolved_dst = [resolved.get("dest", "") for resolved in outbound_data.resolved_data if resolved.get("dest", "") != ""]
                if len(resolved_dst) == 0:
                    resolved_dst = ""
                if len(resolved_dst) == 1:
                    resolved_dst = resolved_dst[0]
                is_mutable_dst = outbound_data.data.get("undetermined_dest", False)
                mutable_dst_vars = outbound_data.data.get("mutable_dest_vars", [])
                mutable_dst_vars = ["{{ " + mv + " }}" for mv in mutable_dst_vars]
                if len(mutable_dst_vars) == 0:
                    mutable_dst_vars = ""
                if len(mutable_dst_vars) == 1:
                    mutable_dst_vars = mutable_dst_vars[0]
                if is_mutable_dst:
                    matched_taskcalls.append(taskcall)
                    message += "- From: {}\n".format(raw_src)
                    message += "  To: {}\n".format(mutable_dst_vars)
                    # message += "      (default value: {})\n".format(
                    #     resolved_dst
                    # )
        matched = len(matched_taskcalls) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_taskcalls, message
