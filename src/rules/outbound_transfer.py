def rule_outbound_transfer(tasks: list):
    matched_tasks = []
    message = ""
    for task in tasks:
        analyzed_data = task.get("analyzed_data", [])
        for single_ad in analyzed_data:
            if single_ad.get("category", "") == "outbound_transfer":
                raw_src = single_ad.get("data", {}).get("src", "")
                raw_dst = single_ad.get("data", {}).get("dest", "")
                resolved_dst = [
                    resolved.get("dest", "")
                    for resolved in single_ad.get("resolved_data", [])
                    if resolved.get("dest", "") != ""
                ]
                if len(resolved_dst) == 0:
                    resolved_dst = ""
                if len(resolved_dst) == 1:
                    resolved_dst = resolved_dst[0]
                is_mutable_dst = single_ad.get("data", {}).get(
                    "undetermined_dest", False
                )
                if is_mutable_dst:
                    matched_tasks.append(task)
                    message += "From: {}\n".format(raw_src)
                    message += "To: {}\n".format(raw_dst)
                    message += "      (default value: {})\n".format(
                        resolved_dst
                    )
    matched = len(matched_tasks) > 0
    message = message[:-1] if message.endswith("\n") else message
    return matched, matched_tasks, message
