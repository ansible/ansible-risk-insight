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

    file = open(args.input)
    data = json.load(file)
    
    results = {}
    builtin_tasks = []
    # extractor
    extractor = BuiltinExtractor()
    for d in data["tasks"]:
        # d = json.loads(task_json_str)
        res = extractor.run(d)
        if res["analyzed_data"] != []:
            builtin_tasks.append(res)
    results["builtin"] = builtin_tasks
    with open(args.output, mode='wt') as file:
        json.dump(results, file, ensure_ascii=False)

if __name__ == "__main__":
    main()

