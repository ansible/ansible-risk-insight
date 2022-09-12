import argparse
import os
import json
import logging
import inspect
from importlib import import_module
from extractors.base import Extractor


def load_extractors():
    extractor_dir = "extractors"
    extractors = []
    extractor_script_names = os.listdir(extractor_dir)
    for extractor_script_name in extractor_script_names:
        if not extractor_script_name.endswith(".py"):
            continue
        extractor_script_name = extractor_script_name.replace(".py", "")
        extractor_module_name = "{}.{}".format(extractor_dir, extractor_script_name)
        tmp_extractor = import_module(extractor_module_name)

        for _, val in vars(tmp_extractor).items():
            if not inspect.isclass(val):
                continue
            instance = val()
            if isinstance(instance, Extractor):
                # skip base class
                if type(instance) == Extractor:
                    continue
                if not instance.enabled:
                    continue
                extractors.append(instance)
    return extractors


def load_tasks_rv(path: str):
    tasks_rv_data = []
    try:
        with open(path, "r") as file:
            for line in file:
                single_tree_data = json.loads(line)
                tasks_rv_data.append(single_tree_data)
    except Exception as e:
        raise ValueError("failed to load the json file {} {}".format(path, e))
    return tasks_rv_data


def analyze(tasks_rv_data: list):
    # extractor
    extractors = load_extractors()

    num = len(tasks_rv_data)
    for i, single_tree_data in enumerate(tasks_rv_data):
        if not isinstance(single_tree_data, dict):
            continue
        if "tasks" not in single_tree_data:
            continue
        for j, task in enumerate(single_tree_data["tasks"]):
            extractor = None
            for _ext in extractors:
                if _ext.match(task):
                    extractor = _ext
                    break
            if extractor is None:
                continue
            task_with_analyzed_data = extractor.analyze(task)
            tasks_rv_data[i]["tasks"][j] = task_with_analyzed_data
        logging.debug("analyze() {}/{} done".format(i + 1, num))
    return tasks_rv_data


def main():
    parser = argparse.ArgumentParser(
        prog="analyze.py",
        description="analyze tasks",
        epilog="end",
        add_help=True,
    )

    parser.add_argument(
        "-i",
        "--input",
        default="",
        help="path to the input json (tasks_rv.json)",
    )
    parser.add_argument("-o", "--output", default="", help="path to the output json")

    args = parser.parse_args()

    tasks_rv_data = load_tasks_rv(args.input)
    tasks_rv_data = analyze(tasks_rv_data)

    if args.output != "":
        lines = [json.dumps(single_tree_data) for single_tree_data in tasks_rv_data]
        with open(args.output, mode="wt") as file:
            file.write("\n".join(lines))


if __name__ == "__main__":
    main()
