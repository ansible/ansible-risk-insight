import argparse
import json
import yaml

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
        line_nums = finding_data.get("line_nums", [])
        line_num_str = "{} - {}".format(line_nums[0], line_nums[1]) if len(line_nums) == 2 else "?"
        yaml_lines = finding_data.get("yaml_lines", "")
        _lines = "\n".join(["   " + line for line in yaml_lines.split("\n") if line != ""])
        output_lines += "[{}] {}\n".format(risk_level, message)
        output_lines += "{} line: {}\n".format(file, line_num_str)
        output_lines += _lines + "\n"
        output_lines += message_detail
    else:
        message_detail = finding_data.get("message_detail", "")
        output_lines += message_detail
    return output_lines


def main():
    parser = argparse.ArgumentParser(
        prog='show_report.py',
        description='Show report.json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to the input json (report.json)')

    args = parser.parse_args()

    report_data = []
    with open(args.input, "r") as file:
        report_data = json.load(file)

    total_playbook_num = len([d for d in report_data if d.get("type", "") == "playbook"])
    risk_playbook_num = len([d for d in report_data if d.get("type", "") == "playbook" and d.get("summary", {}).get("risk_found", False)])
    total_role_num = len([d for d in report_data if d.get("type", "") == "role"])
    risk_role_num = len([d for d in report_data if d.get("type", "") == "role" and d.get("summary", {}).get("risk_found", False)])
    
    print("playbook:")
    print("  total: {}".format(total_playbook_num))
    print("  risk found: {}".format(risk_playbook_num))
    print("role:")
    print("  total: {}".format(total_role_num))
    print("  risk found: {}".format(risk_role_num))
    print("-" * 90)

    final_report = []
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
        print("{} {}".format(single_report["type"].upper(), single_report["name"]))
        print("called by: {}".format(single_report["called_by"]))
        print("findings:")
        for f_type, findings in findings_per_type.items():
            print("  {}".format(f_type))
            for finding in findings:
                print("    {}".format(finding))
        print("-" * 90)

        final_report.append(single_report)

if __name__ == "__main__":
    main()

