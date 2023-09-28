import os
import glob
import argparse
from ansible_risk_insight.findings import Findings
from ansible_risk_insight.risk_assessment_model import RAMClient


default_priority_file_path_in_ram = "indices/collections_sorted_by_download_count.txt"


class RAMSlimGenerator:
    def __init__(self, ram_all_dir, out_dir) -> None:
        self.ram_all_dir = ram_all_dir
        self.ram_slim_dir = out_dir

    def load_priority_list(self, fpath):
        priority_list = []
        if fpath:
            with open(fpath, "r") as file:
                for line in file:
                    name = line.replace("\n", "")
                    if name.startswith("collection "):
                        name = name.split(" ")[-1]
                    priority_list.append(name)
        return priority_list

    def gen_slim(self, priority_file=None):
        priority_list = []
        if priority_file:
            priority_list = self.load_priority_list(fpath=priority_file)

        # find findings.json from ram-all dir
        files = glob.glob(f"{self.ram_all_dir}/collections/findings/**/findings.json", recursive=True)

        files = sort_with_priority(files, priority_list)

        ram_client = RAMClient(root_dir=self.ram_slim_dir)
        total = len(files)
        for i, f_json in enumerate(files):
            _name = f_json.split("/collections/findings/")[1].split("/")[0]

            print(f"\r[{i+1}/{total}] {_name}            ", end="")

            findings = Findings.load(fpath=f_json)
            if not findings:
                continue
            if not isinstance(findings, Findings):
                continue
            if not isinstance(findings.root_definitions, dict):
                continue
            definitions = findings.root_definitions.get("definitions", {})
            if "modules" not in definitions:
                continue

            # remove all types other than `modules` and `collections`
            # NOTE: `collections` are necessary to register `redirects` to module_index
            #        but it should be removed later
            definitions = {
                "modules": definitions["modules"],
                "collections": definitions["collections"],
            }
            findings.root_definitions["definitions"] = definitions
            findings.ext_definitions = {}

            # register modules and redirects to module_index
            ram_client.register_indices_to_ram(findings=findings)
            # remove `collections` here
            findings.root_definitions["definitions"].pop("collections")

            relative_path = f_json.replace(self.ram_all_dir, "").strip("/")
            dest_path = os.path.join(self.ram_slim_dir, relative_path)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            findings.dump(fpath=dest_path)

    def copy_priority_file(self, priority_file=None):
        if not priority_file:
            return

        if not os.path.exists(priority_file):
            return

        body = ""
        with open(priority_file, "r") as src_file:
            body = src_file.read()

        dest_priority_file = os.path.join(self.ram_slim_dir, default_priority_file_path_in_ram)
        with open(dest_priority_file, "w") as dest_file:
            dest_file.write(body)
        return

    def run(self, priority_file=None):
        self.gen_slim(priority_file=priority_file)
        self.copy_priority_file(priority_file=priority_file)


def sort_with_priority(findings_json_list, priority_list):
    if not priority_list:
        return findings_json_list

    sorted_list = []
    for pname in priority_list:
        found = False
        for fpath in findings_json_list:
            query = "/" + pname + "/"
            if query in fpath:
                sorted_list.append(fpath)
                found = True
            if found:
                break

    for fpath in findings_json_list:
        if fpath in sorted_list:
            continue
        sorted_list.append(fpath)
    return sorted_list


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument("-d", "--dir", help="path to ram-all dir (input)")
    parser.add_argument("-o", "--out-dir", help="path to ram slim dir (output)")
    parser.add_argument(
        "-p",
        "--priority",
        help="a list of target names sorted by the priority order.\n"
        "(default to `indices/collections_sorted_by_download_count.txt` in ram-all dir if exists)",
    )
    args = parser.parse_args()

    ram_all_dir = args.dir
    out_dir = args.out_dir
    priority_file = args.priority
    if not priority_file:
        default_priority_path = os.path.join(ram_all_dir, "indices/collections_sorted_by_download_count.txt")
        if os.path.exists(default_priority_path):
            priority_file = default_priority_path

    if not os.path.exists(ram_all_dir):
        raise ValueError(f"ram-all dir does not exist: {ram_all_dir}")

    rsg = RAMSlimGenerator(ram_all_dir, out_dir)
    rsg.run(priority_file=priority_file)
