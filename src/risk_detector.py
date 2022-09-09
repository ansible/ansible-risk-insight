import argparse
import os
import logging
import inspect
from importlib import import_module
from tabulate import tabulate
from keyutil import detect_type, key_delimiter
from analyzer import load_tasks_rv
from rules.base import Rule, subject_placeholder


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


def load_rules():
    rule_dir = "rules"
    rules = []
    rule_script_names = os.listdir(rule_dir)
    for rule_script_name in rule_script_names:
        if not rule_script_name.endswith(".py"):
            continue
        rule_script_name = rule_script_name.replace(".py", "")
        rule_module_name = "{}.{}".format(rule_dir, rule_script_name)
        tmp_rule = import_module(rule_module_name)
        for _, val in vars(tmp_rule).items():
            if not inspect.isclass(val):
                continue
            instance = val()
            if isinstance(instance, Rule):
                # skip base class
                if type(instance) == Rule:
                    continue
                if not instance.enabled:
                    continue
                rules.append(instance)
    return rules


def make_subject_str(playbook_num: int, role_num: int):
    subject = ""
    if playbook_num > 0 and role_num > 0:
        subject = "playbooks/roles"
    elif playbook_num > 0:
        subject = "playbooks"
    elif role_num > 0:
        subject = "roles"
    return subject


def detect(tasks_rv_data: list, collection_name: str = ""):
    rules = load_rules()
    extra_check_args = {}
    if collection_name != "":
        extra_check_args["collection_name"] = collection_name
    result_txt = ""
    result_txt += "-" * 90 + "\n"
    result_txt += "Ansible Risk Insight Report\n"
    result_txt += "-" * 90 + "\n"
    report_num = 1

    playbook_count = {"total": 0, "risk": 0}
    role_count = {"total": 0, "risk": 0}

    separate_report = {}
    role_to_playbook_mappings = {}
    risk_found_playbooks = set()

    tmp_result_txt = ""
    num = len(tasks_rv_data)
    for i, single_tree_data in enumerate(tasks_rv_data):
        if not isinstance(single_tree_data, dict):
            continue
        tree_root_key = single_tree_data.get("root_key", "")
        tree_root_type = detect_type(tree_root_key)
        tree_root_name = key2name(tree_root_key)

        is_playbook = tree_root_type == "playbook"
        if is_playbook:
            playbook_count["total"] += 1

            tasks = single_tree_data.get("tasks", [])
            for task in tasks:
                parts = task.get("defined_in").split("/")
                if parts[0] == "roles":
                    role_name = parts[1]
                    _mappings = role_to_playbook_mappings.get(role_name, [])
                    if tree_root_name not in _mappings:
                        _mappings.append(tree_root_name)
                    role_to_playbook_mappings[role_name] = _mappings
        else:
            role_count["total"] += 1

        do_report = False
        tasks = single_tree_data.get("tasks", [])
        tmp_result_txt_alt = ""
        for rule in rules:
            rule_name = rule.name
            matched, _, message = rule.check(tasks, **extra_check_args)
            if rule.separate_report:
                if rule_name not in separate_report:
                    separate_report[rule_name] = {
                        "rule": rule,
                        "matched": [],
                    }
            if matched:
                if rule.separate_report:
                    separate_report[rule_name]["matched"].append(
                        [tree_root_type, tree_root_name, message]
                    )
                else:
                    if not is_playbook:
                        do_report = True
                        tmp_result_txt_alt += rule_name + "\n"
                        tmp_result_txt_alt += indent(message, 0) + "\n"
        if do_report and tmp_result_txt_alt != "":
            tmp_result_txt += "#{} {} - {}\n".format(
                report_num, tree_root_type.upper(), tree_root_name
            )
            used_in_playbooks = role_to_playbook_mappings.get(
                tree_root_name, []
            )
            risk_found_playbooks = risk_found_playbooks.union(
                set(used_in_playbooks)
            )
            if len(used_in_playbooks) > 0:
                tmp_result_txt += "(used_in: {})\n".format(used_in_playbooks)
            tmp_result_txt += tmp_result_txt_alt
            tmp_result_txt += "-" * 90 + "\n"
            report_num += 1
            if is_playbook:
                playbook_count["risk"] += 1
            else:
                role_count["risk"] += 1
        logging.debug("detect() {}/{} done".format(i+1, num))

    if playbook_count["total"] > 0:
        result_txt += "Playbooks\n"
        result_txt += "  Total: {}\n".format(playbook_count["total"])
        result_txt += "  Risk Found: {}\n".format(len(risk_found_playbooks))
    if role_count["total"] > 0:
        result_txt += "Roles\n"
        result_txt += "  Total: {}\n".format(role_count["total"])
        result_txt += "  Risk Found: {}\n".format(role_count["risk"])
    result_txt += "-" * 90 + "\n"

    result_txt += tmp_result_txt

    for label, rule_data in separate_report.items():
        rule = rule_data["rule"]
        table_data = rule_data["matched"]
        result_txt += label + "\n"
        placeholder = subject_placeholder
        subject = make_subject_str(
            playbook_count["total"], role_count["total"]
        )
        table_txt = "  All {} are OK".format(placeholder)
        if rule.all_ok_message != "":
            table_txt = "  {}".format(rule.all_ok_message)
        if len(table_data) > 0:
            table_txt = tabulate(table_data, tablefmt="plain")
        else:
            table_txt = table_txt.replace(placeholder, subject)
        result_txt += indent(table_txt, 0) + "\n"
        result_txt += "-" * 90 + "\n"
    return result_txt


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
