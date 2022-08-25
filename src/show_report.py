import argparse
import json
from tabulate import tabulate


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

def main():
    parser = argparse.ArgumentParser(
        prog='show_report.py',
        description='Show report.json',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to the input json (report.json)')

    args = parser.parse_args()

    report = {}
    with open(args.input, "r") as file:
        report = json.load(file)
    for category, report_per_cat in report.items():
        category_label = category_mappins.get(category, "")
        print("{}".format(category_label))
        labels = label_mappings.get(category, [])
        table = [labels]
        for report_per_cat_per_tree in report_per_cat:
            root_type = report_per_cat_per_tree.get("type", "")
            root_name = report_per_cat_per_tree.get("name", "")
            details = report_per_cat_per_tree.get("details", [])
            row_meta_data = [root_type, root_name]
            for d in details:
                row_detail_data = list(d.values())
                row_data = row_meta_data.copy()
                row_data.extend(row_detail_data)
                table.append(row_data)
        print(tabulate(table))
        print("")

if __name__ == "__main__":
    main()

