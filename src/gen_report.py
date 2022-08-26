import argparse
from asyncio import tasks
import os
import json

from struct5 import detect_type, key_delimiter
from extractor.ansible_builtin import BuiltinExtractor
from rule_dependency_check import check_tasks as check_dependency_by_tasks


_inbound_transfer_key = "inbound_transfer"
_outbound_transfer_key = "outbound_transfer"
_cmd_exec_key = "cmd_exec"
_dependency_key = "dependency"
report_categories = [_inbound_transfer_key, _outbound_transfer_key]
inbound_exec_categories = [_inbound_transfer_key, _cmd_exec_key]
non_execution_programs = ["tar", "gunzip", "unzip", "mv", "cp"]

def make_summary(details: dict):
    summary = {}
    summary["risk_found"] = False
    inbound_count = len(details.get(_inbound_transfer_key, []))
    summary["inbound_count"] = inbound_count
    inbound_execute_count = len([d for d in details.get(_inbound_transfer_key, []) if d.get("executed", False)])
    summary["inbound_execute_count"] = inbound_execute_count
    outbound_count = len(details.get(_outbound_transfer_key, []))
    summary["outbound_count"] = outbound_count
    dep_detail = details.get(_dependency_key, [])
    all_dependency_verified = None
    if len(dep_detail) > 0:
        all_dependency_verified = len(dep_detail[0].get("unverified_dependencies", [])) == 0
    summary["all_dependency_verified"] = all_dependency_verified

    if summary["inbound_count"] > 0 \
        or summary["inbound_execute_count"] > 0 \
        or summary["outbound_count"] > 0 \
        or not summary["all_dependency_verified"]:
        summary["risk_found"] = True

    return summary

class RiskLevel:
    EMPTY = ""
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"
    CRITICAL = "Critical"

def make_findings(details: dict):
    findings = []
    for d in details.get(_inbound_transfer_key, []):
        is_src_mutable = d.get("is_src_mutable", False)
        is_dst_mutable = d.get("is_dst_mutable", False)
        is_executed = d.get("executed", False)
        filepath = d.get("filepath", False)
        level = RiskLevel.EMPTY
        message = ""
        if is_src_mutable and is_executed:
            level = RiskLevel.CRITICAL
            message = "ANY file can be downloaded from ANY url and the file is executed by a task"
        elif is_src_mutable:
            level = RiskLevel.HIGH
            message = "ANY file can be downloaded from ANY url"
        elif is_executed:
            level = RiskLevel.MEDIUM
            message = "a file is downloaded from remote and executed"
        elif is_dst_mutable:
            level = RiskLevel.LOW
            message = "a file is downloaded from remote and can be placed at ANY location"
        else:
            level = RiskLevel.LOW
            message = "a file is downloaded from remote"

        findings.append({
            "risk_level": level,
            "message": message,
            "file": filepath,
        })

    for d in details.get(_outbound_transfer_key, []):
        is_src_mutable = d.get("is_src_mutable", False)
        is_dst_mutable = d.get("is_dst_mutable", False)
        filepath = d.get("filepath", False)
        level = RiskLevel.EMPTY
        message = ""
        if is_dst_mutable:
            level = RiskLevel.HIGH
            message = "ANY remote url can be specified as a destination of outbound file transfer" 
        elif is_src_mutable:
            level = RiskLevel.MEDIUM
            message = "ANY file can be transfered to remote"
        else:
            level = RiskLevel.LOW
            message = "a file is transfered to remote"
        
        findings.append({
            "risk_level": level,
            "message": message,
            "file": filepath,
        })
    
    dep_details = details.get(_dependency_key, [])
    if len(dep_details) > 0:
        unverified_dependencies = dep_details[0].get("unverified_dependencies", [])
        level = RiskLevel.EMPTY
        message = ""
        if len(unverified_dependencies) > 0:
            level = RiskLevel.HIGH
            message = "depending on unverified collections: {}".format(unverified_dependencies) 
        if level != RiskLevel.EMPTY:
            findings.append({
                "risk_level": level,
                "message": message,
            })

    return findings

def inbound_details(details: list):
    detail_data_list = []
    for (ad, task) in details:
        raw_src = ad.get("data", {}).get("src", "")
        resolved_src = [rd.get("src", "") for rd in ad.get("resolved_data", [])]
        if len(resolved_src) == 0: resolved_src = ""
        if len(resolved_src) == 1: resolved_src = resolved_src[0]
        raw_dst = ad.get("data", {}).get("dest", "")
        resolved_dst = [rd.get("dest", "") for rd in ad.get("resolved_data", [])]
        if len(resolved_dst) == 0: resolved_dst = ""
        if len(resolved_dst) == 1: resolved_dst = resolved_dst[0]
        is_src_mutable = ad.get("data", {}).get("undetermined_src", False)
        is_dst_mutable = ad.get("data", {}).get("undetermined_dest", False)
        executed = ad.get("executed", False)
        filepath = task.get("defined_in", "")
        detail_data_list.append({
            "src": raw_src,
            "resolved_src": resolved_src,
            "dst": raw_dst,
            "resolved_dst": resolved_dst,
            "is_src_mutable": is_src_mutable,
            "is_dst_mutable": is_dst_mutable,
            "executed": executed,
            "filepath": filepath,
        })
    return detail_data_list

def outbound_details(details: list):
    detail_data_list = []
    for (ad, task) in details:
        raw_src = ad.get("data", {}).get("src", "")
        resolved_src = [rd.get("src", "") for rd in ad.get("resolved_data", [])]
        if len(resolved_src) == 0: resolved_src = ""
        if len(resolved_src) == 1: resolved_src = resolved_src[0]
        raw_dst = ad.get("data", {}).get("dest", "")
        resolved_dst = [rd.get("dest", "") for rd in ad.get("resolved_data", [])]
        if len(resolved_dst) == 0: resolved_dst = ""
        if len(resolved_dst) == 1: resolved_dst = resolved_dst[0]
        is_src_mutable = ad.get("data", {}).get("undetermined_src", False)
        is_dst_mutable = ad.get("data", {}).get("undetermined_dest", False)
        filepath = task.get("defined_in", "")
        detail_data_list.append({
            "src": raw_src,
            "resolved_src": resolved_src,
            "dst": raw_dst,
            "resolved_dst": resolved_dst,
            "is_src_mutable": is_src_mutable,
            "is_dst_mutable": is_dst_mutable,
            "filepath": filepath,
        })
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

def gen_report(tasks_rv_data: list, verified_collections: list, check_mode: bool = False):
    report = []
    # extractor
    extractor = BuiltinExtractor()
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
        details = {
            _inbound_transfer_key: [],
            _outbound_transfer_key: [],
            _dependency_key: [],
        }
        ad_tasks = {
            _inbound_transfer_key: [],
            _outbound_transfer_key: [],
            _dependency_key: [],
        }
    
        tasks = single_tree_data.get("tasks", [])
        inbound_exec_datas = []
        for task in tasks:
            res = extractor.run(task)
            analyzed_data = res.get("analyzed_data", [])
            task["analyzed_data"] = analyzed_data
            
            for ad in analyzed_data:
                category = ad.get("category", "")
                if category in report_categories:
                    ad_tasks[category].append((ad, task))
                if category in inbound_exec_categories:
                    inbound_exec_datas.append((ad, task))

        ad_tasks[_inbound_transfer_key], inbound_exec_task_pairs = embed_inbound_exec(inbound_exec_datas, ad_tasks[_inbound_transfer_key])
        
        for cat in report_categories:
            if len(ad_tasks[cat]) == 0:
                continue
            details_per_cat = []
            if cat == _inbound_transfer_key:
                details_per_cat = inbound_details(ad_tasks[cat])
            elif cat == _outbound_transfer_key:
                details_per_cat = outbound_details(ad_tasks[cat])
            details[cat] = details_per_cat

        verified, unverified = check_dependency_by_tasks(tasks, verified_collections)
        details[_dependency_key] = [{"verified_dependencies": verified, "unverified_dependencies": unverified}]
        single_report["details"] = details

        single_report["summary"] = make_summary(details)
        single_report["findings"] = make_findings(details)

        report.append(single_report)

        if check_mode:
            separator = "-" * 50
            for (inbound_task, exec_task) in inbound_exec_task_pairs:
                print("CHECK_DATA_INBOUND:{}".format(json.dumps(inbound_task)))
                print("CHECK_DATA_EXEC:{}".format(json.dumps(exec_task)))
                print(separator)
    return report

def main():
    parser = argparse.ArgumentParser(
        prog='gen_report.py',
        description='Generate report.json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to the input json (tasks_rv.json)')
    parser.add_argument('-o', '--output', default="", help='path to the output json')
    parser.add_argument('-s', '--silent', action='store_true', help='do not output the reports to stdout even when \"--output\" is not specified')
    parser.add_argument('--check', action='store_true', help='show analyzed_data for checking')

    args = parser.parse_args()

    # TODO: from args
    verified_collections = []

    tasks_rv_data = load_tasks_rv(args.input)
    report = gen_report(tasks_rv_data, verified_collections, args.check)
    
    if args.output != "":
        with open(args.output, mode='wt') as file:
            json.dump(report, file, ensure_ascii=False)
    elif not args.silent:
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

