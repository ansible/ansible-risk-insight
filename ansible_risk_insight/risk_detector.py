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
import json
import traceback
from typing import List
import time

import ansible_risk_insight.logger as logger
from .models import AnsibleRunContext, ARIResult, TargetResult, NodeResult, RuleResult, Rule, SpecMutation
from .keyutil import detect_type, key_delimiter
from .analyzer import load_taskcalls_in_trees
from .utils import load_classes_in_dir


rule_versions_filename = "rule_versions.json"


def key2name(key: str):
    _type = detect_type(key)
    if _type == "playbook":
        return os.path.basename(key.split(key_delimiter)[-1])
    elif _type == "role":
        return key.split(key_delimiter)[-1]


def load_rule_versions_file(filepath: str):
    if not os.path.exists(filepath):
        return {}

    version_dict = {}
    with open(filepath, "r") as file:
        for line in file:
            d = None
            try:
                d = json.loads(line)
            except Exception:
                pass
            if not d or not isinstance(d, dict):
                continue
            rule_id = d.get("rule_id")
            if not rule_id:
                continue
            commit_id = d.get("commit_id")
            version_dict[rule_id] = commit_id
    return version_dict


def load_rules(rules_dir: str = "", rule_id_list: list = [], fail_on_error: bool = False):
    if not rules_dir:
        return []
    rules_dir_list = rules_dir.split(":")
    _rules = []
    for _rules_dir in rules_dir_list:
        versions_file = os.path.join(_rules_dir, rule_versions_filename)
        versions_dict = {}
        if os.path.exists(versions_file):
            versions_dict = load_rule_versions_file(versions_file)
        _rule_classes, _errors_for_this_dir = load_classes_in_dir(_rules_dir, Rule, fail_on_error=fail_on_error)
        if _errors_for_this_dir:
            if fail_on_error:
                raise ValueError("error occurred while loading rule directory: " + "; ".join(_errors_for_this_dir))
            else:
                logger.warning("some rules are skipped by the following errors: " + "; ".join(_errors_for_this_dir))
        for r in _rule_classes:
            try:
                _rule = r()
                # if `rule_id_list` is provided, filter out rules that are not in the list
                if rule_id_list:
                    if _rule.rule_id not in rule_id_list:
                        continue
                if versions_dict:
                    if _rule.rule_id in versions_dict:
                        _rule.commit_id = versions_dict[_rule.rule_id]
                _rules.append(_rule)
            except Exception:
                exc = traceback.format_exc()
                msg = f"failed to load a rule `{r}`: {exc}"
                if fail_on_error:
                    raise ValueError(msg)
                else:
                    logger.warning(f"The rule {r} was skipped: {msg}")

    # sort by rule_id
    _rules = sorted(_rules, key=lambda r: int(r.rule_id[-3:]))

    # sort by `rules` configuration for ARIScanner
    if rule_id_list:

        def index(_list, x):
            if x.rule_id in _list:
                return _list.index(x.rule_id)
            else:
                return len(_list)

        _rules = sorted(_rules, key=lambda r: index(rule_id_list, r))

    # sort by precedence
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


def detect(contexts: List[AnsibleRunContext], rules_dir: str = "", rules: list = []):
    rules = load_rules(rules_dir, rules, False)

    report_num = 1

    playbook_count = {"total": 0, "risk_found": 0}
    role_count = {"total": 0, "risk_found": 0}

    data_report = {"summary": {}, "details": [], "ari_result": None}
    role_to_playbook_mappings = {}
    risk_found_playbooks = set()

    ari_result = ARIResult()
    spec_mutations = {}

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
                start_time = time.time()
                r_result = RuleResult(file=t.file_info(), rule=rule.get_metadata())
                try:
                    matched = rule.match(ctx)
                    if matched:
                        tmp_result = rule.process(ctx)
                        if tmp_result:
                            r_result = tmp_result
                        r_result.matched = matched
                    r_result.duration = round((time.time() - start_time) * 1000, 6)
                    if rule.spec_mutation:
                        detail = r_result.get_detail()
                        if isinstance(detail, dict):
                            s_mutations = detail.get("spec_mutations", [])
                            for s_mutation in s_mutations:
                                if not isinstance(s_mutation, SpecMutation):
                                    continue
                                spec_mutations[s_mutation.key] = s_mutation
                except Exception:
                    exc = traceback.format_exc()
                    r_result.error = f"failed to execute the rule `{rule.rule_id}`: {exc}"
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
        logger.debug("detect() {}/{} done".format(i + 1, num))

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
    data_report["spec_mutations"] = spec_mutations

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
