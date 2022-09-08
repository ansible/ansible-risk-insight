<<<<<<< HEAD
from rules.base import Rule


non_execution_programs: list = ["tar", "gunzip", "unzip", "mv", "cp"]


class DownloadExecRule(Rule):
    name: str = "Download & Exec"
    enabled: bool = True

    # IN: tasks with "analyzed_data" (i.e. output from analyzer.py)
    # OUT: matched: bool, matched_tasks: list[task | tuple[task]], message: str
    def check(self, tasks: list):
        # list downloaded files from "inbound_transfer" tasks
        download_files_and_tasks = []
        for task in tasks:
            analyzed_data = task.get("analyzed_data", [])
            for single_ad in analyzed_data:
                if single_ad.get("category", "") == "inbound_transfer":
                    src = single_ad.get("data", {}).get("src", "")
                    dst = single_ad.get("data", {}).get("dest", "")
                    if isinstance(src, list):
                        src = [s for s in src if s.replace(" ", "") != "{{item}}"]
                    if isinstance(dst, str) and dst != "":
                        download_files_and_tasks.append((dst, task, src))
                    elif isinstance(dst, list) and len(dst) > 0:
                        for _d in dst:
                            download_files_and_tasks.append((_d, task, src))
        # check if the downloaded files are executed in "cmd_exec" tasks
        matched_tasks = []
        message = ""
        found = []
        for task in tasks:
            analyzed_data = task.get("analyzed_data", [])
            for single_ad in analyzed_data:
                if single_ad.get("category", "") == "cmd_exec":
                    cmd_str = single_ad.get("data", {}).get("cmd", "")
                    for i, (
                        downloaded_file,
                        download_task,
                        download_src,
                    ) in enumerate(download_files_and_tasks):
                        if i in found:
                            continue
                        if _is_executed(cmd_str, downloaded_file):
                            matched_tasks.append((download_task, task))
                            found.append(i)
                            message += "- Download block: {}, line: {}\n".format(
                                download_task.get("defined_in", ""),
                                _make_line_num_expr(
                                    download_task.get("line_num_in_file", [])
                                ),
                            )
                            message += "  Exec block: {}, line: {}\n".format(
                                task.get("defined_in", ""),
                                _make_line_num_expr(
                                    task.get("line_num_in_file", [])
                                ),
                            )
                            message += '  Mutable Variables: "{}"\n'.format(
                                download_src
                            )
        matched = len(matched_tasks) > 0
        message = message[:-1] if message.endswith("\n") else message
        return matched, matched_tasks, message
=======

non_execution_programs = ["tar", "gunzip", "unzip", "mv", "cp"]


def rule_download_and_exec(tasks: list):
    # list downloaded files from "inbound_transfer" tasks
    download_files_and_tasks = []
    for task in tasks:
        analyzed_data = task.get("analyzed_data", [])
        for single_ad in analyzed_data:
            if single_ad.get("category", "") == "inbound_transfer":
                src = single_ad.get("data", {}).get("src", "")
                dst = single_ad.get("data", {}).get("dest", "")
                if isinstance(dst, str) and dst != "":
                    download_files_and_tasks.append((dst, task, src))
                elif isinstance(dst, list) and len(dst) > 0:
                    for _d in dst:
                        download_files_and_tasks.append((_d, task, src))
    # check if the downloaded files are executed in "cmd_exec" tasks
    matched_tasks = []
    message = ""
    for task in tasks:
        analyzed_data = task.get("analyzed_data", [])
        for single_ad in analyzed_data:
            if single_ad.get("category", "") == "cmd_exec":
                cmd_str = single_ad.get("data", {}).get("cmd", "")
                for (
                    downloaded_file,
                    download_task,
                    download_src,
                ) in download_files_and_tasks:
                    if _is_executed(cmd_str, downloaded_file):
                        matched_tasks.append((download_task, task))
                        message += "Download block: {}, line: {}\n".format(
                            download_task.get("defined_in", ""),
                            _make_line_num_expr(
                                download_task.get("line_num_in_file", [])
                            ),
                        )
                        message += "Exec block: {}, line: {}\n".format(
                            task.get("defined_in", ""),
                            _make_line_num_expr(
                                task.get("line_num_in_file", [])
                            ),
                        )
                        message += 'Mutable Variables: "{}"\n'.format(
                            download_src
                        )
    matched = len(matched_tasks) > 0
    message = message[:-1] if message.endswith("\n") else message
    return matched, matched_tasks, message
>>>>>>> f4e25374 (add rules & anlyzer & risk_detector)


def _make_line_num_expr(line_num_parts: list):
    line_num_expr = "?"
    if len(line_num_parts) == 2:
        line_num_expr = "{} - {}".format(line_num_parts[0], line_num_parts[1])
    return line_num_expr


def _is_executed(cmd_str, target):
    lines = cmd_str.splitlines()
    found = False
    for line in lines:
        if target not in line:
            continue
        if line.startswith(target):
            found = True
        if _is_primary_command_target(line, target):
            found = True
        if found:
            break
    return found


def _is_primary_command_target(line, target):
    parts = []
    is_in_variable = False
    concat_p = ""
    for p in line.split(" "):
        if "{{" in p and "}}" not in p:
            is_in_variable = True
        if "}}" in p:
            is_in_variable = False
        concat_p += " " + p if concat_p != "" else p
        if not is_in_variable:
            parts.append(concat_p)
            concat_p = ""
    current_index = 0
    found_index = -1
    for p in parts:
        if current_index == 0:
            program = p if "/" not in p else p.split("/")[-1]
            # filter out some specific non-exec patterns
            if program in non_execution_programs:
                break
        if p.startswith(target):
            found_index = current_index
            break
        if p.startswith("-"):
            continue
        current_index += 1
    # "<target.sh> option1 option2" => found_index == 0
    # python -u <target.py> ==> found_index == 1
    is_primay_target = found_index >= 0 and found_index <= 1
    return is_primay_target
