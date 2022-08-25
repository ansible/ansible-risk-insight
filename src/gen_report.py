import argparse
import os
import json

from struct5 import detect_type, key_delimiter
from extractor.ansible_builtin import BuiltinExtractor
from rule_dependency_check import check_tasks as check_dependency_by_tasks


report_categories = ["inbound_transfer", "outbound_transfer"]
inbound_exec_categories = ["inbound_transfer", "cmd_exec"]
field_mappings = {
    "inbound_transfer": "src",
    "outbound_transfer": "dest",
}

def inbound_details(details):
    detail_data_list = []
    for d in details:
        raw_src = d.get("data", {}).get("src", "")
        resolved_src = [rd.get("src", "") for rd in d.get("resolved_data", [])]
        if len(resolved_src) == 0: resolved_src = ""
        if len(resolved_src) == 1: resolved_src = resolved_src[0]
        customizable = d.get("data", {}).get("undetermined_src", False)
        executed = d.get("executed", False)
        detail_data_list.append({
            "source": raw_src,
            "value": resolved_src,
            "customizable": customizable,
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
        customizable = d.get("data", {}).get("undetermined_dest", False)
        detail_data_list.append({
            "destination": raw_dst,
            "value": resolved_dst,
            "customizable": customizable,
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
        if category == "inbound_transfer":
            src = d.get("data", {}).get("src", "")
            dst = d.get("data", {}).get("dest", "")
            if src != "" and dst != "":
                src_dst_list.append((src, dst))
        elif category == "cmd_exec":
            cmd_str = d.get("data", {}).get("cmd", "")
            lines = cmd_str.splitlines()
            found = False
            exec_src_name = ""
            for line in lines:
                for (src, dst) in src_dst_list:
                    if line.startswith(dst):
                        found = True
                        exec_src_name = src
                        break
                if found:
                    break
            if found:
                exec_src_list.append(exec_src_name)
    for i_d in inbound_data_list:
        if not isinstance(i_d, dict):
            continue
        src = d.get("data", {}).get("src", "")
        i_d["executed"] = src in exec_src_list
    return inbound_data_list

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
    _dependency_key = "dependency"
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
        for task in tasks:
            res = extractor.run(task)
            analyzed_data = res.get("analyzed_data", [])
            for ad in analyzed_data:
                category = ad.get("category", "")
                field_name = field_mappings.get(category, "")
                if field_name == "":
                    continue
                if category in report_categories:
                    report_for_this_tree[category].append(ad)
                if category in inbound_exec_categories:
                    inbound_exec_datas.append(ad)

        report_for_this_tree["inbound_transfer"] = embed_inbound_exec(inbound_exec_datas, report_for_this_tree["inbound_transfer"])
        
        for cat in report_categories:
            if len(report_for_this_tree[cat]) == 0:
                continue
            details = []
            if cat == "inbound_transfer":
                details = inbound_details(report_for_this_tree[cat])
            elif cat == "outbound_transfer":
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

