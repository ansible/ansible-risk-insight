import os
import glob
import argparse
import shutil
import json
from ansible_risk_insight.findings import Findings
from ansible_risk_insight.risk_assessment_model import RAMClient


class SubsetGenerator:
    def __init__(self, ram_all_dir, out_dir) -> None:
        self.ram_all_dir = ram_all_dir
        self.ram_subset_dir = out_dir

        self.priority_data = []
        self.copied_findings_json_list = []

    def _get_dependencies(self, findings_path):
        dep_list = []
        with open(findings_path, "r") as f:
            findings = json.load(f)
            dependencies = findings.get("dependencies", [])
            for dep in dependencies:
                metadata = dep.get("metadata", {})
                _type = metadata.get("type", "")
                _name = metadata.get("name", "")
                if _type and _name:
                    dep_list.append((_type, _name))
        return dep_list

    def gen_dependency_ram(self, findings_path):
        dep_list = self._get_dependencies(findings_path)
        self.gen_subset(dep_list)
        return

    def gen_subset(self, subset_list):
        # find findings.json from ram-all dir
        for _type, _name in subset_list:
            files = []
            if _type == "collection":
                files = glob.glob(f"{self.ram_all_dir}/collections/findings/{_name}/**/findings.json", recursive=True)
            elif _type == "role":
                files = glob.glob(f"{self.ram_all_dir}/roles/findings/{_name}/**/findings.json", recursive=True)

            if len(files) == 0:
                print(f"findings.json not found. ({_type} {_name})")
                continue
            for f_json in files:
                relative_path = f_json.replace(self.ram_all_dir, "").strip("/")
                dest_path = os.path.join(self.ram_subset_dir, relative_path)
                dest_dir = os.path.dirname(dest_path)
                os.makedirs(dest_dir, exist_ok=True)
                if not os.path.exists(dest_path):
                    shutil.copy2(f_json, dest_path)
                self.gen_dependency_ram(f_json)

                if dest_path not in self.copied_findings_json_list:
                    self.copied_findings_json_list.append(dest_path)

    def gen_list(self, input_list, priority_file=None):
        # load subset list
        subset_list = []
        with open(input_list, "r") as f:
            lines = f.readlines()
            for line in lines:
                parts = line.split()
                _type = parts[0]
                _name = parts[1]
                if _type != "collection" and _type != "role":
                    print(f"invalid type {_type}. type should be role or collection.")
                    continue
                subset_list.append((_type, _name))
        if priority_file:
            priority_list = self.load_priority_list(fpath=priority_file)
            subset_list = self.sort_with_priority(subset_list=subset_list, priority_list=priority_list)
        return subset_list

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

    def sort_with_priority(self, subset_list, priority_list):
        if not priority_list:
            return subset_list

        sorted_list = []
        for pname in priority_list:
            found = False
            for (_type, _name) in subset_list:
                if pname == _name:
                    sorted_list.append((_type, _name))
                    found = True
                if found:
                    break

        for fpath in subset_list:
            if fpath in sorted_list:
                continue
            sorted_list.append(fpath)
        return sorted_list

    def recreate_indices(self):
        if not self.copied_findings_json_list:
            return

        # use RAM client just to register index data
        ram_client = RAMClient(root_dir=self.ram_subset_dir)
        for findings_json_path in self.copied_findings_json_list:
            findings = Findings.load(fpath=findings_json_path)
            if not findings:
                continue
            ram_client.register_indices_to_ram(findings=findings)

    def run(self, input_list, priority_file=None):
        subset_list = self.gen_list(input_list, priority_file)
        self.gen_subset(subset_list)
        self.recreate_indices()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument("-d", "--dir", help="path to ram-all dir")
    parser.add_argument("-i", "--input-list", help='collection/role list of the form "collection community.general"')
    parser.add_argument("-o", "--out-dir", help="path to ram subset dir")
    parser.add_argument(
        "-p",
        "--priority",
        help="a list of target names sorted by the priority order.\n"
        "(default to `indices/collections_sorted_by_download_count.txt` in ram-all dir if exists)",
    )
    args = parser.parse_args()

    ram_all_dir = args.dir
    input_list = args.input_list
    out_dir = args.out_dir
    priority_file = args.priority
    if not priority_file:
        default_priority_path = os.path.join(ram_all_dir, "indices/collections_sorted_by_download_count.txt")
        if os.path.exists(default_priority_path):
            priority_file = default_priority_path

    if not os.path.exists(ram_all_dir):
        raise ValueError(f"ram-all dir does not exist: {ram_all_dir}")

    if not os.path.exists(input_list):
        raise ValueError(f"subset list does not exist: {input_list}")

    sg = SubsetGenerator(ram_all_dir, out_dir)
    sg.run(input_list=input_list, priority_file=priority_file)
