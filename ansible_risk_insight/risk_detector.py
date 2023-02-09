# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2022 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import os
import logging
from typing import List

from .models import AnsibleRunContext, ARIResult, TargetResult, NodeResult, RuleResult, Rule
from .keyutil import detect_type, key_delimiter
from .analyzer import load_taskcalls_in_trees
from .utils import load_classes_in_dir


def key2name(key: str):
    _type = detect_type(key)
    if _type == "playbook":
        return os.path.basename(key.split(key_delimiter)[-1])
    elif _type == "role":
        return key.split(key_delimiter)[-1]


def load_rules(rules_dir: str = ""):
    rules_dir_list = rules_dir.split(":")
    _rules = []
    for _rules_dir in rules_dir_list:
        _rule_classes = load_classes_in_dir(_rules_dir, Rule)
        for r in _rule_classes:
            try:
                _rule = r()
                _rules.append(_rule)
            except Exception:
                raise ValueError(f"failed to load a rule: {r}")
    _rules = sorted(_rules, key=lambda r: int(r.rule_id[-3:]))
    _rules = sorted(_rules, key=lambda r: r.precedence)

    return _rules


def make_subject_str(playbook_num: int, role_num: int):
    subject = ""
    if playbook_num > 0 and role_num > 0:
        subject = "playbooks/roles"
    elif playbook_num > 0:
        subject = "playbooks"
    elif role_num > 0:
        subject = "roles"
    return subject


def detect(contexts: List[AnsibleRunContext], rules_dir: str = ""):
    rules = load_rules(rules_dir)

    report_num = 1

    playbook_count = {"total": 0, "risk_found": 0}
    role_count = {"total": 0, "risk_found": 0}

    data_report = {"summary": {}, "details": [], "ari_result": None}
    role_to_playbook_mappings = {}
    risk_found_playbooks = set()

    ari_result = ARIResult()

    num = len(contexts)
    for i, ctx in enumerate(contexts):
        if not isinstance(ctx, AnsibleRunContext):
            continue
        tree_root_key = ctx.root_key
        tree_root_type = detect_type(tree_root_key)
        tree_root_name = key2name(tree_root_key)

        t_result = TargetResult(
            target_type=tree_root_type,
            target_name=tree_root_name,
        )

        is_playbook = tree_root_type == "playbook"
        if is_playbook:
            playbook_count["total"] += 1

            for task in ctx.taskcalls:
                parts = task.spec.defined_in.split("/")
                if parts[0] == "roles":
                    role_name = parts[1]
                    _mappings = role_to_playbook_mappings.get(role_name, [])
                    if tree_root_name not in _mappings:
                        _mappings.append(tree_root_name)
                    role_to_playbook_mappings[role_name] = _mappings
        else:
            role_count["total"] += 1

        for t in ctx:
            ctx.current = t
            n_result = NodeResult(node=t)
            for rule in rules:
                if not rule.enabled:
                    continue
                matched = rule.match(ctx)
                r_result = RuleResult(file=t.file_info(), rule=rule.get_metadata())
                if matched:
                    tmp_result = rule.process(ctx)
                    if tmp_result:
                        r_result = tmp_result
                    r_result.matched = matched
                n_result.rules.append(r_result)
            t_result.nodes.append(n_result)
        ari_result.targets.append(t_result)

        do_report = False
        output_dict = {}
        data_dict = {}
        rule_dict = {}
        rule_count = {
            "total": 0,
            "rule_applied": 0,
            "risk_found": 0,
        }
        for rule in rules:
            rule_dict[rule.name] = rule
            if not rule.enabled:
                continue
            rule_count["total"] += 1
            rule_count["rule_applied"] += 1
            results = []
            triggered_results = []
            triggered_messages = []
            for t in ctx:
                ctx.current = t
                if not rule.match(ctx):
                    continue
                result = rule.process(ctx)
                if not result:
                    continue
                results.append(result)
                if result.verdict:
                    triggered_results.append(result)
                    triggered_messages.append(rule.print(result))
            if triggered_results:
                rule_count["risk_found"] += 1
                do_report = True
                messages = triggered_messages
                detail_data = [r.detail for r in triggered_results]
                output_dict[rule.name] = "\n".join(messages)
                data_dict[rule.name] = detail_data
        result_list = [
            {
                "rule": {
                    "name": rule_name,
                    "version": rule_dict[rule_name].version,
                    "severity": rule_dict[rule_name].severity,
                    "tags": rule_dict[rule_name].tags,
                },
                "output": output_dict[rule_name],
                "data": data_dict[rule_name],
            }
            for rule_name in output_dict
        ]
        data_report["details"].append(
            {
                "type": tree_root_type,
                "name": tree_root_name,
                "rule_count": rule_count,
                "results": result_list,
            }
        )

        if do_report:
            used_in_playbooks = role_to_playbook_mappings.get(tree_root_name, [])
            risk_found_playbooks = risk_found_playbooks.union(set(used_in_playbooks))
            report_num += 1
            if is_playbook:
                playbook_count["risk_found"] += 1
            else:
                role_count["risk_found"] += 1
        logging.debug("detect() {}/{} done".format(i + 1, num))

    if playbook_count["total"] > 0:
        data_report["summary"]["playbooks"] = {
            "total": playbook_count["total"],
            "risk_found": playbook_count["risk_found"],
        }
    if role_count["total"] > 0:
        data_report["summary"]["roles"] = {
            "total": role_count["total"],
            "risk_found": role_count["risk_found"],
        }
    data_report["ari_result"] = ari_result

    return data_report


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
        help="path to the input json (tasks_in_trees.json)",
    )
    parser.add_argument("-o", "--output", default="", help="path to the output json")
    parser.add_argument("-v", "--verbose", default="", help="show details during the process")

    args = parser.parse_args()

    tasks_in_trees = load_taskcalls_in_trees(args.input)

    detect(tasks_in_trees)


if __name__ == "__main__":
    main()
