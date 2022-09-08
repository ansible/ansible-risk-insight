from rules.base import Rule


class InboundTransferRule(Rule):
    name: str = "InboundTransfer"
    enabled: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, tasks: list):
        matched_tasks = []
        message = ""
        for task in tasks:
            analyzed_data = task.get("analyzed_data", [])
            for single_ad in analyzed_data:
                if single_ad.get("category", "") == "inbound_transfer":
                    raw_src = single_ad.get("data", {}).get("src", "")
                    raw_dst = single_ad.get("data", {}).get("dest", "")
                    if isinstance(raw_src, list):
                        raw_src = [s for s in raw_src if s.replace(" ", "") != "{{item}}"]
                    resolved_src = [
                        resolved.get("src", "")
                        for resolved in single_ad.get("resolved_data", [])
                        if resolved.get("src", "") != ""
                    ]
                    if len(resolved_src) == 0:
                        resolved_src = ""
                    if len(resolved_src) == 1:
                        resolved_src = resolved_src[0]
                    is_mutable_src = single_ad.get("data", {}).get(
                        "undetermined_src", False
                    )
                    if is_mutable_src:
                        matched_tasks.append(task)
                        message += "- From: {}\n".format(raw_src)
                        # message += "      (default value: {})\n".format(
                        #     resolved_src
                        # )
                        message += "  To: {}\n".format(raw_dst)
        matched = len(matched_tasks) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_tasks, message
