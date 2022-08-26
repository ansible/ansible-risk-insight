import argparse
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
unarchive_programs = ["tar", "gunzip", "unzip"]

def inbound_details(details):
    detail_data_list = []
    for d in details:
        raw_src = d.get("data", {}).get("src", "")
        resolved_src = [rd.get("src", "") for rd in d.get("resolved_data", [])]
        if len(resolved_src) == 0: resolved_src = ""
        if len(resolved_src) == 1: resolved_src = resolved_src[0]
        mutable_var = d.get("data", {}).get("undetermined_src", False)
        executed = d.get("executed", False)
        detail_data_list.append({
            "source": raw_src,
            "value": resolved_src,
            "mutable_var": mutable_var,
            "executed": executed,
        })
    return detail_data_list

def outbound_details(details):
    detail_data_list = []
    for d in details:
        raw_dst = d.get("data", {}).get("dest", "")
        resolved_dst = [rd.get("dest", "") for rd in d.get("resolved_data", [])]
        if len(resolved_dst) == 0: resolved_dst = ""
        if len(resolved_dst) == 1: resolved_dst = resolved_dst[0]
        mutable_var = d.get("data", {}).get("undetermined_dest", False)
        detail_data_list.append({
            "destination": raw_dst,
            "value": resolved_dst,
            "mutable_var": mutable_var,
        })
    return detail_data_list

def embed_inbound_exec(data_list: list, inbound_data_list: list):
    src_dst_list = []
    exec_src_list = []
    for d in data_list:
        if not isinstance(d, dict):
            continue
        category = d.get("category", "")
        if category not in inbound_exec_categories:
            continue
        if category == _inbound_transfer_key:
            src = d.get("data", {}).get("src", "")
            dst = d.get("data", {}).get("dest", "")
            if src != "" and dst != "":
                src_dst_list.append((src, dst))
        elif category == "cmd_exec":
            cmd_str = d.get("data", {}).get("cmd", "")
            found = False
            exec_src_name = ""
            for (src, dst) in src_dst_list:
                targets = []
                if isinstance(dst, str):
                    targets = [dst]
                if isinstance(dst, list):
                    targets = dst
                for target in targets:
                    if is_executed(cmd_str, target):
                        found = True
                        exec_src_name = src
                        break
            if found:
                exec_src_list.append(exec_src_name)
    for i_d in inbound_data_list:
        if not isinstance(i_d, dict):
            continue
        src = i_d.get("data", {}).get("src", "")
        i_d["executed"] = src in exec_src_list
    return inbound_data_list

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
            if program in unarchive_programs:
                break
        if target in p:
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

def main():
    parser = argparse.ArgumentParser(
        prog='gen_report.py',
        description='Generate report.json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to the input json (tasks_rv.json)')
    parser.add_argument('-o', '--output', default="", help='path to the output json')
    parser.add_argument('--check', action='store_true', help='show analyzed_data for checking')

    args = parser.parse_args()

    # TODO: from args
    verified_collections = []

    tasks_rv_data = []
    try:
        with open(args.input, "r") as file:
            for line in file:
                single_tree_data = json.loads(line)
                tasks_rv_data.append(single_tree_data)
    except Exception as e:
        raise ValueError("failed to load the json file {} {}".format(args.input, e))

    report = {cat: [] for cat in report_categories}
    
    report[_dependency_key] = []
    # extractor
    extractor = BuiltinExtractor()
    for single_tree_data in tasks_rv_data:
        if not isinstance(single_tree_data, dict):
            continue
        tree_root_key = single_tree_data.get("root_key", "")
        tree_root_type = detect_type(tree_root_key)
        tree_root_name = key2name(tree_root_key)
        tasks = single_tree_data.get("tasks", [])
        report_for_this_tree = {cat: [] for cat in report_categories}
        inbound_exec_datas = []
        tasks_for_check = []
        for i, task in enumerate(tasks):
            res = extractor.run(task)
            analyzed_data = res.get("analyzed_data", [])
            task["analyzed_data"] = analyzed_data
            
            is_task_for_check = False
            for ad in analyzed_data:
                category = ad.get("category", "")
                if category == _inbound_transfer_key:
                    is_task_for_check = True
                if category in report_categories:
                    report_for_this_tree[category].append(ad)
                if category in inbound_exec_categories:
                    inbound_exec_datas.append(ad)
            
            if is_task_for_check:
                tasks_for_check.append(tasks[i])
                if i+1<len(tasks): tasks_for_check.append(tasks[i+1])
                if i+2<len(tasks): tasks_for_check.append(tasks[i+2])
        
        if args.check:
            separator = "-" * 50
            for i, t in enumerate(tasks_for_check):
                if i%3 == 0:
                    print(separator)
                    print("showing analyzed_data for a \"{}\" task and 2 trailing tasks:".format(_inbound_transfer_key))
                check_data = {
                    "rn": t.get("resolved_name", ""),
                    "ad": t.get("analyzed_data", []),
                    "key": t.get("key", ""),
                }
                print(json.dumps(check_data))
            print(separator)

        report_for_this_tree[_inbound_transfer_key] = embed_inbound_exec(inbound_exec_datas, report_for_this_tree[_inbound_transfer_key])
        
        for cat in report_categories:
            if len(report_for_this_tree[cat]) == 0:
                continue
            details = []
            if cat == _inbound_transfer_key:
                details = inbound_details(report_for_this_tree[cat])
            elif cat == _outbound_transfer_key:
                details = outbound_details(report_for_this_tree[cat])
            report[cat].append({"type": tree_root_type, "name": tree_root_name, "details": details})

        ok, findings, resolution = check_dependency_by_tasks(tasks, verified_collections)
        report[_dependency_key].append({"type": tree_root_type, "name": tree_root_name, "details": [{"result": ok, "findings": findings, "resolution": resolution}]})

    if args.output != "":
        with open(args.output, mode='wt') as file:
            json.dump(report, file, ensure_ascii=False)
    else:
        print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()

