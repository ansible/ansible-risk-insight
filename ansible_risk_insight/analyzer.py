import argparse
import json
import logging
from typing import List
from ansible_risk_insight import risk_annotators
from .models import Task, TaskCallsInTree


def load_risk_annotators():
    _risk_annotators = []
    for annotator in risk_annotators.__all__:
        _risk_annotators.append(getattr(risk_annotators, annotator)())
    return _risk_annotators


def load_taskcalls_in_trees(path: str) -> List[TaskCallsInTree]:
    taskcalls_in_trees = []
    try:
        with open(path, "r") as file:
            for line in file:
                taskcalls_in_tree = TaskCallsInTree()
                taskcalls_in_tree.from_json(line)
                taskcalls_in_trees.append(taskcalls_in_tree)
    except Exception as e:
        raise ValueError("failed to load the json file {} {}".format(path, e))
    return taskcalls_in_trees


def analyze(taskcalls_in_trees: List[TaskCallsInTree]):
    # risk annotator
    risk_annotators = load_risk_annotators()

    num = len(taskcalls_in_trees)
    for i, taskcalls_in_tree in enumerate(taskcalls_in_trees):
        if not isinstance(taskcalls_in_tree, TaskCallsInTree):
            continue
        for j, taskcall in enumerate(taskcalls_in_tree.taskcalls):
            annotator = None
            for risk_annotator in risk_annotators:
                if not risk_annotator.enabled:
                    continue
                if risk_annotator.match(taskcall=taskcall):
                    annotator = risk_annotator
                    break
            if annotator is None:
                continue
            annotations = annotator.run(taskcall)
            taskcalls_in_trees[i].taskcalls[j].annotations.extend(annotations)
        logging.debug("analyze() {}/{} done".format(i + 1, num))
    return taskcalls_in_trees


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
        help="path to the input json (taskcalls_in_trees.json)",
    )
    parser.add_argument(
        "-o", "--output", default="", help="path to the output json"
    )

    args = parser.parse_args()

    taskcalls_in_trees = load_taskcalls_in_trees(args.input)
    taskcalls_in_trees = analyze(taskcalls_in_trees)

    if args.output != "":
        lines = [
            json.dumps(single_tree_data)
            for single_tree_data in taskcalls_in_trees
        ]
        with open(args.output, mode="wt") as file:
            file.write("\n".join(lines))


if __name__ == "__main__":
    main()
