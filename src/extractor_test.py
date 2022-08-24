from re import I
import argparse
import sys
import json
import yaml

from extractor.ansible_builtin import BuiltinExtractor

def main():
    parser = argparse.ArgumentParser(
        prog='results2tasks.py',
        description='Load a directory where the dumped Repository json files exist, and output tasks in a simplified format',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-i', '--input', default="", help='path to a directory where result json files exist')
    parser.add_argument('-o', '--output', default="", help='path to the output json')

    args = parser.parse_args()
    # with open(args.input, "r") as file:
    #     tasks = file.readlines()

    try:
        # file = open(args.input)
        with open(args.input, "r") as file:
            tasks = file.readlines()
        # data = json.load(file)
    except Exception as e:
        raise ValueError("failed to load {} {}".format(args.input, e))

    results = {}
    builtin_tasks = []
    # extractor
    extractor = BuiltinExtractor()
    for task in tasks:
        data = json.loads(task)
        for d in data["tasks"]:
            # d = json.loads(task_json_str)
            res = extractor.run(d)
            d["analyzed_data"] = res
        if args.output != "":
            with open(args.output, mode='wt') as file:
                json.dump(data, file, ensure_ascii=False)
        else:
            print(json.dumps(data, indent=2))

if __name__ == "__main__":
    main()

