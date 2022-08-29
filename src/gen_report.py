import argparse
from asyncio import tasks
import os
import json

from keyutil import detect_type, key_delimiter

from context import mutable_types
from extractors.ansible_builtin import AnsibleBuiltinExtractor
from rule_dependency_check import check_tasks as check_dependency_by_tasks
from models import ExecutableType


_inbound_transfer_key = "inbound_transfer"
_outbound_transfer_key = "outbound_transfer"
_mutable_import_key = "mutable_import"
_cmd_exec_key = "cmd_exec"
_dependency_key = "dependency"
_used_in_playbooks_key = "used_in_playbooks"
report_categories = [_inbound_transfer_key, _outbound_transfer_key]
inbound_exec_categories = [_inbound_transfer_key, _cmd_exec_key]
non_execution_programs = ["tar", "gunzip", "unzip", "mv", "cp"]


def make_summary(details: dict):
    summary = {}
    summary["risk_found"] = False  # just default value

    inbound_count = len(details.get(_inbound_transfer_key, []))
    summary["inbound_count"] = inbound_count
    inbound_src_mutable_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_src_mutable", False)
        ]
    )
    inbound_src_domain_mutable_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_src_domain_mutable", False)
        ]
    )
    inbound_src_domain_mutable_and_no_checksum_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_src_domain_mutable_and_no_checksum", False)
        ]
    )
    inbound_src_domain_mutable_and_checksum_mutable_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_src_domain_mutable_and_checksum_mutable", False)
        ]
    )
    inbound_src_entire_variable_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_src_entire_variable", False)
        ]
    )
    inbound_dst_mutable_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_dst_mutable", False)
        ]
    )
    inbound_both_mutable_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("is_src_mutable", False)
            and d.get("is_dst_mutable", False)
        ]
    )
    summary["inbound_detail"] = {}
    summary["inbound_detail"][
        "inbound_src_mutable_count"
    ] = inbound_src_mutable_count
    summary["inbound_detail"][
        "inbound_dst_mutable_count"
    ] = inbound_dst_mutable_count
    summary["inbound_detail"][
        "inbound_both_mutable_count"
    ] = inbound_both_mutable_count
    summary["inbound_detail"][
        "inbound_src_domain_mutable_count"
    ] = inbound_src_domain_mutable_count
    summary["inbound_detail"][
        "inbound_src_domain_mutable_and_no_checksum_count"
    ] = inbound_src_domain_mutable_and_no_checksum_count
    summary["inbound_detail"][
        "inbound_src_domain_mutable_and_checksum_mutable_count"
    ] = inbound_src_domain_mutable_and_checksum_mutable_count
    summary["inbound_detail"][
        "inbound_src_entire_variable_count"
    ] = inbound_src_entire_variable_count

    inbound_execute_count = len(
        [
            d
            for d in details.get(_inbound_transfer_key, [])
            if d.get("executed", False)
        ]
    )
    summary["inbound_execute_count"] = inbound_execute_count

    outbound_count = len(details.get(_outbound_transfer_key, []))
    summary["outbound_count"] = outbound_count
    outbound_src_mutable_count = len(
        [
            d
            for d in details.get(_outbound_transfer_key, [])
            if d.get("is_src_mutable", False)
        ]
    )
    outbound_dst_mutable_count = len(
        [
            d
            for d in details.get(_outbound_transfer_key, [])
            if d.get("is_dst_mutable", False)
        ]
    )
    outbound_dst_domain_mutable_count = len(
        [
            d
            for d in details.get(_outbound_transfer_key, [])
            if d.get("is_dst_domain_mutable", False)
        ]
    )
    outbound_dst_entire_variable_count = len(
        [
            d
            for d in details.get(_outbound_transfer_key, [])
            if d.get("is_dst_entire_variable", False)
        ]
    )
    outbound_both_mutable_count = len(
        [
            d
            for d in details.get(_outbound_transfer_key, [])
            if d.get("is_src_mutable", False)
            and d.get("is_dst_mutable", False)
        ]
    )
    outbound_local_to_remote_count = len(
        [
            d
            for d in details.get(_outbound_transfer_key, [])
            if d.get("is_local_to_remote", False)
        ]
    )
    summary["outbound_detail"] = {}
    summary["outbound_detail"][
        "outbound_src_mutable_count"
    ] = outbound_src_mutable_count
    summary["outbound_detail"][
        "outbound_dst_mutable_count"
    ] = outbound_dst_mutable_count
    summary["outbound_detail"][
        "outbound_both_mutable_count"
    ] = outbound_both_mutable_count
    summary["outbound_detail"][
        "outbound_dst_domain_mutable_count"
    ] = outbound_dst_domain_mutable_count
    summary["outbound_detail"][
        "outbound_dst_entire_variable_count"
    ] = outbound_dst_entire_variable_count
    summary["outbound_detail"][
        "outbound_local_to_remote_count"
    ] = outbound_local_to_remote_count

    # mutable_import_count = len(details.get(_mutable_import_key, []))
    # summary["mutable_import_count"] = mutable_import_count

    dep_detail = details.get(_dependency_key, [])
    all_dependency_verified = None
    if len(dep_detail) > 0:
        all_dependency_verified = (
            len(dep_detail[0].get("unverified_dependencies", [])) == 0
        )
    summary["all_dependency_verified"] = all_dependency_verified

    if (
        summary["inbound_count"] > 0
        or summary["inbound_execute_count"] > 0
        or summary["outbound_count"] > 0
    ):
        summary["risk_found"] = True

    return summary

class RiskLevel:
    EMPTY = ""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

class FindingType:
    INBOUND = "InboundTransfer"
    OUTBOUND = "OutboundTransfer"
    DOWNLOAD_EXEC = "Download & Exec"

def make_findings(details: dict):
    findings = []
    for d in details.get(_inbound_transfer_key, []):
        raw_src = d.get("src", "")
        resolved_src = d.get("resolved_src", "")
        resolved_dst = d.get("resolved_dst", "")
        is_src_mutable = d.get("is_src_mutable", False)
        is_dst_mutable = d.get("is_dst_mutable", False)
        is_executed = d.get("executed", False)
        filepath = d.get("filepath", "")
        _task = d.get("task", {})
        line_nums = _task.get("line_num_in_file", [])

        exec_filepath = ""
        _exec_task = {}
        exec_line_nums = []
        if is_executed:
            _exec_task = d.get("exec_task", {})
            exec_filepath = _exec_task.get("defined_in", "")
            exec_line_nums = _exec_task.get("line_num_in_file", "")

        level = RiskLevel.EMPTY
        message = ""
        message_detail = ""
        if is_src_mutable and is_executed:
            level = RiskLevel.CRITICAL
            message = (
                "ANY file can be downloaded from ANY url and the file is"
                " executed by a task"
            )
            message_detail += 'Mutable Variables: "{}"'.format(raw_src)
        elif is_src_mutable:
            level = RiskLevel.HIGH
            message = "ANY file can be downloaded from ANY url"
            message_detail += '"{}" --> "{}"'.format(raw_src, resolved_dst)
        elif is_executed:
            level = RiskLevel.MEDIUM
            message = "a file is downloaded from remote and executed"
        elif is_dst_mutable:
            level = RiskLevel.LOW
            message = (
                "a file is downloaded from remote and can be placed at ANY"
                " location"
            )
        else:
            level = RiskLevel.LOW
            message = "a file is downloaded from remote"

        findings.append(
            {
                "type": FindingType.DOWNLOAD_EXEC
                if is_executed
                else FindingType.INBOUND,
                "risk_level": level,
                "message": message,
                "message_detail": message_detail,
                "file": filepath,
                "line_nums": line_nums,
                "exec_file": exec_filepath,
                "exec_line_nums": exec_line_nums,
            }
        )

    for d in details.get(_outbound_transfer_key, []):
        raw_dst = d.get("dst", "")
        resolved_src = d.get("resolved_src", "")
        is_src_mutable = d.get("is_src_mutable", False)
        is_dst_mutable = d.get("is_dst_mutable", False)
        filepath = d.get("filepath", "")
        level = RiskLevel.EMPTY
        message = ""
        message_detail = ""
        if is_dst_mutable:
            level = RiskLevel.HIGH
            message = (
                "ANY remote url can be specified as a destination of outbound"
                " file transfer"
            )
            message_detail += '"{}" --> "{}"'.format(resolved_src, raw_dst)
        elif is_src_mutable:
            level = RiskLevel.MEDIUM
            message = "ANY file can be transfered to remote"
        else:
            level = RiskLevel.LOW
            message = "a file is transfered to remote"

        findings.append(
            {
                "type": FindingType.OUTBOUND,
                "risk_level": level,
                "message": message,
                "message_detail": message_detail,
                "file": filepath,
            }
        )

    return findings

def inbound_details(details: list, inbound_exec_task_pairs: list):
    detail_data_list = []
    for (ad, task) in details:
        raw_src = ad.get("data", {}).get("src", "")
        resolved_src = [
            rd.get("src", "") for rd in ad.get("resolved_data", [])
        ]
        if len(resolved_src) == 0:
            resolved_src = ""
        if len(resolved_src) == 1:
            resolved_src = resolved_src[0]
        raw_dst = ad.get("data", {}).get("dest", "")
        resolved_dst = [
            rd.get("dest", "") for rd in ad.get("resolved_data", [])
        ]
        if len(resolved_dst) == 0:
            resolved_dst = ""
        if len(resolved_dst) == 1:
            resolved_dst = resolved_dst[0]
        is_src_mutable = ad.get("data", {}).get("undetermined_src", False)
        is_dst_mutable = ad.get("data", {}).get("undetermined_dest", False)
        executed = ad.get("executed", False)
        filepath = task.get("defined_in", "")
        is_src_domain_mutable = False
        is_src_domain_mutable_and_no_checksum = False
        is_src_domain_mutable_and_checksum_mutable = False
        is_src_entire_variable = False
        _src_list = []
        if isinstance(raw_src, str):
            _src_list = [raw_src]
        if isinstance(raw_src, list):
            if "{{ item }}" in raw_src:
                _src_list = [
                    s for s in raw_src if s != "{{ item }}" and "{{" in s
                ]
                raw_src = _src_list
            else:
                _src_list = raw_src
        for _src in _src_list:
            if is_src_mutable:
                if _src.startswith("{{") or "://{{" in _src:
                    is_src_domain_mutable = True
                    checksum = task.get("module_options", {}).get(
                        "checksum", ""
                    )
                    if checksum == "":
                        is_src_domain_mutable_and_no_checksum = True
                    else:
                        if "{{" in checksum:
                            is_src_domain_mutable_and_checksum_mutable = True
            if (
                _src.startswith("{{")
                and _src.endswith("}}")
                and len(_src[:-2].split("}}")) == 1
            ):
                is_src_entire_variable = True
        paired_exec_task = {}
        if is_executed:
            inbound_task_key = task.get("key", "")
            for (inbound_task, exec_task) in inbound_exec_task_pairs:
                if inbound_task.get("key", "") == inbound_task_key:
                    paired_exec_task = exec_task
                    break
        detail_data_list.append(
            {
                "src": raw_src,
                "resolved_src": resolved_src,
                "dst": raw_dst,
                "resolved_dst": resolved_dst,
                "is_src_mutable": is_src_mutable,
                "is_src_domain_mutable": is_src_domain_mutable,
                "is_src_domain_mutable_and_no_checksum":
                    is_src_domain_mutable_and_no_checksum,
                "is_src_domain_mutable_and_checksum_mutable":
                    is_src_domain_mutable_and_checksum_mutable,
                "is_src_entire_variable": is_src_entire_variable,
                "is_dst_mutable": is_dst_mutable,
                "executed": executed,
                "filepath": filepath,
                "task": task,
                "exec_task": paired_exec_task,
            }
        )
    return detail_data_list


def outbound_details(details: list):
    detail_data_list = []
    for (ad, task) in details:
        raw_src = ad.get("data", {}).get("src", "")
        resolved_src = [
            rd.get("src", "") for rd in ad.get("resolved_data", [])
        ]
        if len(resolved_src) == 0:
            resolved_src = ""
        if len(resolved_src) == 1:
            resolved_src = resolved_src[0]
        raw_dst = ad.get("data", {}).get("dest", "")
        resolved_dst = [
            rd.get("dest", "") for rd in ad.get("resolved_data", [])
        ]
        if len(resolved_dst) == 0:
            resolved_dst = ""
        if len(resolved_dst) == 1:
            resolved_dst = resolved_dst[0]
        is_src_mutable = ad.get("data", {}).get("undetermined_src", False)
        is_dst_mutable = ad.get("data", {}).get("undetermined_dest", False)
        # if remote_src is yes for ansible.builtin.copy
        # it just copy a file inside remote machine
        is_local_to_remote = not task.get("module_options", {}).get(
            "remote_src", False
        )
        filepath = task.get("defined_in", "")
        is_dst_domain_mutable = False
        is_dst_entire_variable = False
        _dst_list = []
        if isinstance(raw_dst, str):
            _dst_list = [raw_dst]
        if isinstance(raw_dst, list):
            _dst_list = raw_dst
        for _dst in _dst_list:
            if is_src_mutable:
                if _dst.startswith("{{") or "://{{" in _dst:
                    is_dst_domain_mutable = True
            if (
                _dst.startswith("{{")
                and _dst.endswith("}}")
                and len(_dst[:-2].split("}}")) == 1
            ):
                is_dst_entire_variable = True
        detail_data_list.append(
            {
                "src": raw_src,
                "resolved_src": resolved_src,
                "dst": raw_dst,
                "resolved_dst": resolved_dst,
                "is_local_to_remote": is_local_to_remote,
                "is_src_mutable": is_src_mutable,
                "is_dst_mutable": is_dst_mutable,
                "is_dst_domain_mutable": is_dst_domain_mutable,
                "is_dst_entire_variable": is_dst_entire_variable,
                "filepath": filepath,
                "task": task,
            }
        )
    return detail_data_list


def embed_inbound_exec(data_list: list, inbound_data_list: list):
    src_dst_list = []
    exec_src_list = []
    inbound_exec_task_pairs = []
    for (ad, task) in data_list:
        if not isinstance(ad, dict):
            continue
        category = ad.get("category", "")
        if category not in inbound_exec_categories:
            continue
        if category == _inbound_transfer_key:
            src = ad.get("data", {}).get("src", "")
            dst = ad.get("data", {}).get("dest", "")
            if src != "" and dst != "":
                src_dst_list.append((src, dst, task))
        elif category == "cmd_exec":
            cmd_str = ad.get("data", {}).get("cmd", "")
            found = False
            exec_src_name = ""
            inbound_task = None
            for (src, dst, _inbound_task) in src_dst_list:
                targets = []
                if isinstance(dst, str):
                    targets = [dst]
                if isinstance(dst, list):
                    targets = dst
                for target in targets:
                    if is_executed(cmd_str, target):
                        found = True
                        exec_src_name = src
                        inbound_task = _inbound_task
                        break
            if found:
                exec_src_list.append(exec_src_name)
                inbound_exec_task_pairs.append((inbound_task, task))
    for (ad, _) in inbound_data_list:
        if not isinstance(ad, dict):
            continue
        src = ad.get("data", {}).get("src", "")
        ad["executed"] = src in exec_src_list
    return inbound_data_list, inbound_exec_task_pairs


def is_primary_command_target(line, target):
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


def is_executed(cmd_str, target):
    lines = cmd_str.splitlines()
    found = False
    for line in lines:
        if target not in line:
            continue
        if line.startswith(target):
            found = True
        if is_primary_command_target(line, target):
            found = True
        if found:
            break
    return found


def check_mutable_import(tasks: list):
    detail_data_list = []
    for task in tasks:
        exec_type = task.get("executable_type", "")
        if exec_type != ExecutableType.ROLE_TYPE:
            continue
        filepath = task.get("defined_in", "")
        module_options = task.get("module_options", "")
        resolved_variables = task.get("resolved_variables", [])
        if len(resolved_variables) == 0:
            continue
        if (
            len(
                [
                    v
                    for v in resolved_variables
                    if v.get("type", "") in mutable_types
                ]
            )
            == 0
        ):
            continue
        detail_data_list.append(
            {
                "option": module_options,
                "resolved_variables": resolved_variables,
                "filepath": filepath,
            }
        )
    return detail_data_list


def is_primary_command_target(line, target):
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
            # typically, the downloaded file is just unarchived without execution
            # we do not count it as inbound_exec, so exit the loop here
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

def is_executed(cmd_str, target):
    lines = cmd_str.splitlines()
    found = False
    for line in lines:
        if target not in line:
            continue
        if line.startswith(target):
            found = True
        if is_primary_command_target(line, target):
            found = True
        if found:
            break
    return found

def check_mutable_import(tasks: list):
    detail_data_list = []
    for task in tasks:
        exec_type = task.get("executable_type", "")
        if exec_type != ExecutableType.ROLE_TYPE:
            continue
        filepath = task.get("defined_in", "")
        module_options = task.get("module_options", "")
        resolved_variables = task.get("resolved_variables", [])
        if len(resolved_variables) == 0:
            continue
        if len([v for v in resolved_variables if v.get("type", "") in mutable_types]) == 0:
            continue
        detail_data_list.append({
            "option": module_options,
            "resolved_variables": resolved_variables,
            "filepath": filepath,
        })
    return detail_data_list

def key2name(key: str):
    _type = detect_type(key)
    if _type == "playbook":
        return os.path.basename(key.split(key_delimiter)[-1])
    elif _type == "role":
        return key.split(key_delimiter)[-1]


def load_tasks_rv(path: str):
    tasks_rv_data = []
    try:
        with open(path, "r") as file:
            for line in file:
                single_tree_data = json.loads(line)
                tasks_rv_data.append(single_tree_data)
    except Exception as e:
        raise ValueError("failed to load the json file {} {}".format(path, e))
    return tasks_rv_data


def gen_report(
    tasks_rv_data: list, verified_collections: list, check_mode: bool = False
):
    report = []
    # extractor
    extractor = AnsibleBuiltinExtractor()

    role_to_playbook_mappings = {}
    for single_tree_data in tasks_rv_data:
        if not isinstance(single_tree_data, dict):
            continue
        tree_root_key = single_tree_data.get("root_key", "")
        tree_root_type = detect_type(tree_root_key)
        tree_root_name = key2name(tree_root_key)
        single_report = {
            "type": tree_root_type,
            "name": tree_root_name,
            "summary": {},
            "findings": [],
            "details": {},
        }
        ad_tasks = {
            _inbound_transfer_key: [],
            _outbound_transfer_key: [],
        }

        tasks = single_tree_data.get("tasks", [])
        inbound_exec_datas = []
        for task in tasks:
            if tree_root_type == "playbook":
                parts = task.get("defined_in").split("/")
                if parts[0] == "roles":
                    role_name = parts[1]
                    _mappings = role_to_playbook_mappings.get(role_name, [])
                    if tree_root_name not in _mappings:
                        _mappings.append(tree_root_name)
                    role_to_playbook_mappings[role_name] = _mappings
                continue

            res = extractor.run(task)
            analyzed_data = res.get("analyzed_data", [])
            task["analyzed_data"] = analyzed_data

            for ad in analyzed_data:
                category = ad.get("category", "")
                if category in report_categories:
                    ad_tasks[category].append((ad, task))
                if category in inbound_exec_categories:
                    inbound_exec_datas.append((ad, task))

        (
            ad_tasks[_inbound_transfer_key],
            inbound_exec_task_pairs,
        ) = embed_inbound_exec(
            inbound_exec_datas, ad_tasks[_inbound_transfer_key]
        )

        details = {
            _inbound_transfer_key: [],
            _outbound_transfer_key: [],
            # _mutable_import_key: [],
            _dependency_key: [],
            _used_in_playbooks_key: [],
        }
        for cat in report_categories:
            if len(ad_tasks[cat]) == 0:
                continue
            details_per_cat = []
            if cat == _inbound_transfer_key:
                details_per_cat = inbound_details(
                    ad_tasks[cat], inbound_exec_task_pairs
                )
            elif cat == _outbound_transfer_key:
                details_per_cat = outbound_details(ad_tasks[cat])
            details[cat] = details_per_cat

        # mutable_import_details = check_mutable_import(tasks)
        # details[_mutable_import_key] = mutable_import_details

        verified, unverified = check_dependency_by_tasks(
            tasks, verified_collections
        )
        details[_dependency_key] = [
            {
                "verified_dependencies": verified,
                "unverified_dependencies": unverified,
            }
        ]
        details[_used_in_playbooks_key] = role_to_playbook_mappings.get(
            tree_root_name, []
        )
        single_report["details"] = details

        single_report["summary"] = make_summary(details)
        single_report["findings"] = make_findings(details)

        report.append(single_report)

        if check_mode:
            separator = "-" * 50
            for (inbound_task, exec_task) in inbound_exec_task_pairs:
                print(
                    "CHECK_DATA_INBOUND:{}".format(json.dumps(inbound_task))
                )
                print("CHECK_DATA_EXEC:{}".format(json.dumps(exec_task)))
                print(separator)
    return report


def main():
    parser = argparse.ArgumentParser(
        prog="gen_report.py",
        description="Generate report.json",
        epilog="end",
        add_help=True,
    )

    parser.add_argument(
        "-i",
        "--input",
        default="",
        help="path to the input json (tasks_rv.json)",
    )
    parser.add_argument(
        "-o", "--output", default="", help="path to the output json"
    )
    parser.add_argument(
        "-s",
        "--silent",
        action="store_true",
        help=(
            'do not output the reports to stdout even when "--output" is not'
            " specified"
        ),
    )
    parser.add_argument(
        "--check", action="store_true", help="show analyzed_data for checking"
    )

    args = parser.parse_args()

    # TODO: from args
    verified_collections = []

    tasks_rv_data = load_tasks_rv(args.input)
    report = gen_report(tasks_rv_data, verified_collections, args.check)

    if args.output != "":
        with open(args.output, mode="wt") as file:
            json.dump(report, file, ensure_ascii=False)
    elif not args.silent:
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
