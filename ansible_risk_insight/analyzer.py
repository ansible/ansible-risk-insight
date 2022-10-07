import argparse
import json
import logging
from typing import List
from ansible_risk_insight import extractors
from .models import Task, TasksInTree


def load_extractors():
    _extractors = []
    for extractor in extractors.__all__:
        _extractors.append(getattr(extractors, extractor)())
    return _extractors


def load_tasks_in_trees(path: str) -> List[TasksInTree]:
    tasks_in_trees = []
    try:
        with open(path, "r") as file:
            for line in file:
                tasks_in_tree = TasksInTree()
                tasks_in_tree.from_json(line)
                tasks_in_trees.append(tasks_in_tree)
    except Exception as e:
        raise ValueError("failed to load the json file {} {}".format(path, e))
    return tasks_in_trees


def analyze(tasks_in_trees: list):
    # extractor
    extractors = load_extractors()

    num = len(tasks_in_trees)
    for i, tasks_in_tree in enumerate(tasks_in_trees):
        if not isinstance(tasks_in_tree, TasksInTree):
            continue
        for j, task in enumerate(tasks_in_tree.tasks):
            extractor = None
            for _ext in extractors:
                if not _ext.enabled:
                    continue
                if _ext.match(task=task):
                    extractor = _ext
                    break
            if extractor is None:
                continue
            task_with_analyzed_data = extractor.analyze(task)
            tasks_in_trees[i].tasks[j] = task_with_analyzed_data
        logging.debug("analyze() {}/{} done".format(i + 1, num))
    return tasks_in_trees


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
        help="path to the input json (tasks_in_trees.json)",
    )
    parser.add_argument(
        "-o", "--output", default="", help="path to the output json"
    )

    args = parser.parse_args()

    tasks_in_trees = load_tasks_in_trees(args.input)
    tasks_in_trees = analyze(tasks_in_trees)

    if args.output != "":
        lines = [
            json.dumps(single_tree_data)
            for single_tree_data in tasks_in_trees
        ]
        with open(args.output, mode="wt") as file:
            file.write("\n".join(lines))


if __name__ == "__main__":
    main()
