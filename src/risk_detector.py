import argparse
import os
from importlib import import_module

from keyutil import detect_type, key_delimiter
from analyzer import load_tasks_rv


def indent(multi_line_txt, level=0):
    lines = multi_line_txt.splitlines()
    lines = [
        " " * level + line for line in lines if line.replace(" ", "") != ""
    ]
    return "\n".join(lines)


def key2name(key: str):
    _type = detect_type(key)
    if _type == "playbook":
        return os.path.basename(key.split(key_delimiter)[-1])
    elif _type == "role":
        return key.split(key_delimiter)[-1]


def get_rules(rule_dir: str = ""):
    rule_module_prefix = ""
    if rule_dir == "":
        rule_dir = "rules"
        rule_module_prefix = "rules"
    else:
        rule_module_prefix = rule_dir.replace("/", ".")
        rule_module_prefix = (
            rule_module_prefix[:-1]
            if rule_module_prefix.endswith(".")
            else rule_module_prefix
        )
    rules = {}
    rule_script_names = os.listdir(rule_dir)
    for rule_script_name in rule_script_names:
        if not rule_script_name.endswith(".py"):
            continue
        rule_script_name = rule_script_name.replace(".py", "")
        rule_module_name = "{}.{}".format(
            rule_module_prefix, rule_script_name
        )
        tmp_rule = import_module(rule_module_name)
        for key, val in vars(tmp_rule).items():
            if key.startswith("rule_") and callable(val):
                if rule_module_name not in rules:
                    rules[rule_module_name] = {}
                rules[rule_module_name][key] = val
    return rules


def detect(tasks_rv_data: list):
    rules = get_rules()
    for i, single_tree_data in enumerate(tasks_rv_data):
        if not isinstance(single_tree_data, dict):
            continue
        tree_root_key = single_tree_data.get("root_key", "")
        tree_root_type = detect_type(tree_root_key)
        tree_root_name = key2name(tree_root_key)
        print(
            "#{} {} - {}".format(
                i + 1, tree_root_type.upper(), tree_root_name
            )
        )
        tasks = single_tree_data.get("tasks", [])
        for _, rule_module in rules.items():
            for rule_func_name, rule_func in rule_module.items():
                rule_name = rule_func_name.replace("rule_", "")
                matched, matched_tasks, messge = rule_func(tasks)
                if matched:
                    print(rule_name.upper())
                    print(indent(messge, 4))


def main():
    parser = argparse.ArgumentParser(
        prog="risk_detector.py",
        description="Detect risks from tasks by checking rules",
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
        "-v", "--verbose", default="", help="show details during the process"
    )

    args = parser.parse_args()

    tasks_rv_data = load_tasks_rv(args.input)

    detect(tasks_rv_data)


if __name__ == "__main__":
    main()
