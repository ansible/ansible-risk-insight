import argparse
import json

from extractor.ansible_builtin import BuiltinExtractor


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
    extractor = BuiltinExtractor()

    for single_tree_data in tasks_rv_data:
        if not isinstance(single_tree_data, dict):
            continue
        if "tasks" not in single_tree_data:
            continue
        for task in single_tree_data["tasks"]:
            res = extractor.run(task)
            analyzed_data = res.get("analyzed_data", [])
            task["analyzed_data"] = analyzed_data

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
    parser.add_argument(
        "-o", "--output", default="", help="path to the output json"
    )

    args = parser.parse_args()

    tasks_rv_data = load_tasks_rv(args.input)
    tasks_rv_data = analyze(tasks_rv_data)

    if args.output != "":
        lines = [
            json.dumps(single_tree_data) for single_tree_data in tasks_rv_data
        ]
        with open(args.output, mode="wt") as file:
            file.write("\n".join(lines))


if __name__ == "__main__":
    main()
