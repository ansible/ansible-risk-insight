import os
import json
import logging
import argparse
from struct4 import Repository


logging.basicConfig()
logging.getLogger().setLevel(logging.INFO)

class Results2Tasks():
    def __init__(self, result_dir="", output=""):
        self.result_dir = result_dir
        self.output = output

    def run(self):
        simple_tasks = []
        files = os.listdir(self.result_dir)
        logging.info("{} files found.".format(len(files)) )

        loaded_file_count = 0
        loaded_task_count = 0
        for fname in files:
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(self.result_dir, fname)

            json_str = ""
            with open(fpath, "r") as file:
                json_str = file.read()
            repo = Repository()
            repo.from_json(json_str)
            loaded_file_count += 1
            for t in repo.task_dict.values():
                simple_task = self.make_simple_task_dict(t)
                simple_tasks.append(simple_task)
                loaded_task_count += 1

        logging.info("{} result files loaded.".format(loaded_file_count))
        logging.info("{} tasks found.".format(loaded_task_count))

        if self.output != "":
            out_str = ""
            for t in simple_tasks:
                line = json.dumps(t) + "\n"
                out_str += line

            with open(self.output, "w") as file:
                file.write(out_str)

    def make_simple_task_dict(self, task):
        d = {}
        d["defined_in"] = task.defined_in
        d["module"] = task.module
        d["name"] = task.name
        d["executable_type"] = task.executable_type
        d["executable"] = task.executable
        d["resolved_name"] = task.resolved_name
        d["possible_candidates"] = task.possible_candidates
        return d


def main():
    parser = argparse.ArgumentParser(
        prog='results2tasks.py',
        description='Load a directory where the dumped Repository json files exist, and output tasks in a simplified format',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-r', '--result-dir', default="", help='path to a directory where result json files exist')
    parser.add_argument('-o', '--output', default="", help='path to the output json')

    args = parser.parse_args()
    r = Results2Tasks(args.result_dir, args.output)
    r.run()


if __name__ == "__main__":
    main()