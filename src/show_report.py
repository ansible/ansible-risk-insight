import argparse
import json
import yaml
from tabulate import tabulate
from gen_report import FindingType

category_mappins = {
    "inbound_transfer": "INBOUND",
    "outbound_transfer": "OUTBOUND",
    "dependency": "DEPENDENCY",
}


label_mappings = {
    "inbound_transfer": ["Type", "Name", "Source", "Value", "Customizable", "Executed"],
    "outbound_transfer": ["Type", "Name", "Destination", "Value", "Customizable"],
    "dependency": ["Type", "Name", "Verified", "Findings", "Resolution"],
}

def make_detail_output(finding_data):
    type = finding_data.get("type", "")
    output_lines = ""
    if type == FindingType.DOWNLOAD_EXEC:
        risk_level = finding_data.get("risk_level", "")
        message = finding_data.get("message", "")
        message_detail = finding_data.get("message_detail", "")
        file = finding_data.get("file", "")
        exec_file = finding_data.get("exec_file", "")
        line_nums = finding_data.get("line_nums", [])
        exec_line_nums = finding_data.get("exec_line_nums", [])
        line_num_str = "{} - {}".format(line_nums[0], line_nums[1]) if len(line_nums) == 2 else "?"
        exec_line_num_str = "{} - {}".format(exec_line_nums[0], exec_line_nums[1]) if len(exec_line_nums) == 2 else "?"
        
        # output_lines += "[{}] {}\n".format(risk_level, message)
        output_lines += "Download block: {}, line: {}\n".format(file, line_num_str)
        output_lines += "Exec block: {}, line: {}\n".format(exec_file, exec_line_num_str)
        output_lines += message_detail
    else:
        message_detail = finding_data.get("message_detail", "")
        output_lines += message_detail
    return output_lines

def indent(multi_line_txt, level=0):
    lines = multi_line_txt.splitlines()
    lines = [" "*level + l for l in lines if l.replace(" ", "") != ""]
    return "\n".join(lines)

def make_display_report(fpath="", detail_report=None):
    report_data = []
    output_lines = []
    output_lines.append("-" * 90)
    output_lines.append("Ansible Risk Insight Report")
    output_lines.append("-" * 90)

    if fpath != "":
        with open(fpath, "r") as file:
            report_data = json.load(file)
    elif detail_report is not None:
        report_data = detail_report

    total_playbook_num = len([d for d in report_data if d.get("type", "") == "playbook"])
    # risk_playbook_num = len([d for d in report_data if d.get("type", "") == "playbook" and d.get("summary", {}).get("risk_found", False)])
    total_role_num = len([d for d in report_data if d.get("type", "") == "role"])
    risk_role_num = len([d for d in report_data if d.get("type", "") == "role" and d.get("summary", {}).get("risk_found", False)])

    risk_playbook_set = set([])
    for single_tree_data in report_data:
        root_type = single_tree_data.get("type", "")
        root_name = single_tree_data.get("name", "")
        risk_found = single_tree_data.get("summary", {}).get("risk_found", False)
        called_by = single_tree_data.get("details", {}).get("used_in_playbooks", [])
        findings = single_tree_data.get("findings", [])
        if len(findings) == 0:
            continue
        if root_type == "role" and risk_found:
            risk_playbook_set = risk_playbook_set.union(set(called_by))
    risk_playbook_num = len(risk_playbook_set)

    if total_playbook_num > 0:
        output_lines.append("playbook:")
        output_lines.append("  total: {}".format(total_playbook_num))
        output_lines.append("  risk found: {}".format(risk_playbook_num))
    if total_role_num > 0:
        output_lines.append("role:")
        output_lines.append("  total: {}".format(total_role_num))
        output_lines.append("  risk found: {}".format(risk_role_num))
    output_lines.append("-" * 90)

    count = 1
    for single_tree_data in report_data:
        root_type = single_tree_data.get("type", "")
        root_name = single_tree_data.get("name", "")
        called_by = single_tree_data.get("details", {}).get("used_in_playbooks", [])
        findings = single_tree_data.get("findings", [])
        if len(findings) == 0:
            continue

        findings_per_type = {
            FindingType.DOWNLOAD_EXEC: [],
            FindingType.INBOUND: [],
            FindingType.OUTBOUND: [],
        }
        for finding_data in findings:
            if not isinstance(finding_data, dict):
                continue
            f_type = finding_data.get("type", "")
            if f_type not in findings_per_type:
                continue
            single_detail = make_detail_output(finding_data)
            findings_per_type[f_type].append(single_detail)
        single_report = {
            "type": root_type,
            "name": root_name,
            "called_by": called_by,
            "findings": findings_per_type,
        }
        output_lines.append("#{} {} - {}".format(count, single_report["type"].upper(), single_report["name"]))
        if len(single_report["called_by"]) > 0:
            output_lines.append("called_by: {}".format(single_report["called_by"]))
        for f_type, findings in findings_per_type.items():
            if len(findings) == 0:
                continue
            _tmp_lines = []
            _tmp_lines.append("{}".format(f_type))
            count_for_this_type = 0
            for finding in findings:
                detail_block = indent(finding, 4)
                if detail_block == "":
                    continue
                _tmp_lines.append(detail_block)
                count_for_this_type += 1
            if count_for_this_type > 0:
                output_lines.extend(_tmp_lines)
        output_lines.append("-" * 90)
        count += 1

    # dependency
    output_lines.append("")
    dep_table = [["TYPE", "NAME", "EXTERNAL DEPENDENCIES"]]
    for single_tree_data in report_data:
        root_type = single_tree_data.get("type", "")
        root_name = single_tree_data.get("name", "")
        unverified_dependencies = single_tree_data.get("details", {}).get("dependency", [])[0].get("unverified_dependencies", [])
        if len(unverified_dependencies) == 0:
            continue
        single_row = [root_type, root_name, unverified_dependencies]
        dep_table.append(single_row)

    table_txt = "External Dependency\n"
    if len(dep_table) > 1:
        table_txt += tabulate(dep_table)
    else:
        table_txt +="    No playbooks/roles have external dependencies"
    output_lines.extend(table_txt.splitlines())
    return "\n".join(output_lines)

def main():
    parser = argparse.ArgumentParser(
        prog='show_report.py',
        description='Show report.json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to the input json (report.json)')

    args = parser.parse_args()

    report = make_display_report(args.input)
    print(report)

if __name__ == "__main__":
    main()

