import argparse
import os
import sys
import json
import traceback
import logging

from gen_report import load_tasks_rv, gen_report


def make_report_file_name(role_name):
    return "role-{}-report.json".format(role_name)

def make_report_file_path(output_dir, role_name):
    return os.path.join(output_dir, make_report_file_name(role_name))

def save_meta_report(meta_report: dict, path: str):
    with open(path, "w") as file:
        json.dump(meta_report, file)
    return

def main():
    parser = argparse.ArgumentParser(
        prog='gen_report_wrapper.py',
        description='Generate report.json for role name list',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to the input file (e.g. \"galaxy_role_sorted_loaded.txt\")')
    parser.add_argument('-p', '--path', default="", help='path to role definitions dir (something like \"~/dev/ansible/var-ari-data/roles\")')
    parser.add_argument('-o', '--output', default="", help='path to the output dir (output file is \"role-<ROLE_NAME>-report.json\")')
    parser.add_argument('--check', action='store_true', help='show analyzed_data for checking')

    args = parser.parse_args()

    if args.input == "":
        logging.error("\"--input\" is required")
        sys.exit(1)

    if args.output == "":
        logging.error("\"--output\" is required")
        sys.exit(1)


    # TODO: from args
    verified_collections = []

    path_placeholder = "/Users/mue/galaxy/roles"

    tasks_rv_path_list = []
    try:
        with open(args.input, "r") as file:
            for line in file:
                _path = line[:-1] if line.endswith("\n") else line
                if args.path != "":
                    _path = _path.replace(path_placeholder, args.path)
                    _path = os.path.normpath(_path)
                tasks_rv_path_list.append(_path)
    except Exception as e:
        raise ValueError("failed to load the input file {} {}".format(args.input, e))

    output_dir = args.output

    for tasks_rv_path in tasks_rv_path_list:
        role_name = tasks_rv_path.split("/")[-2]
        meta_report = {
            "role": role_name,
            "data": None,
            "result": "",
            "error": "",
        }
        err = None
        # step 1: load tasks_rv.json
        tasks_rv_data = None
        try:
            tasks_rv_data = load_tasks_rv(tasks_rv_path)
        except Exception:
            err = "error while loading tasks_rv.json: " + traceback.format_exc()
        if err is not None:
            meta_report["result"] = "failure"
            meta_report["error"] = err
            save_meta_report(meta_report, make_report_file_path(output_dir, role_name))
            continue

        # step 2: generate report
        report = None
        try:
            report = gen_report(tasks_rv_data, verified_collections, args.check)
        except Exception:
            err = "error while generating report: " + traceback.format_exc()
        if err is not None:
            meta_report["result"] = "failure"
            meta_report["error"] = err
            save_meta_report(meta_report, make_report_file_path(output_dir, role_name))
            continue

        meta_report["result"] = "success"
        meta_report["data"] = report
        save_meta_report(meta_report, make_report_file_path(output_dir, role_name))

if __name__ == "__main__":
    main()

