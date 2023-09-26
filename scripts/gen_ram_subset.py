import os
import glob
import argparse
import shutil
import json


class SubsetGenerator():
    def __init__(self, ram_all_dir, out_dir) -> None:
        self.ram_all_dir = ram_all_dir
        self.ram_subset_dir = out_dir

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
    
    def gen_list(self, input_list):
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
        return subset_list



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument("-d", "--dir", help='path to ram-all dir')
    parser.add_argument("-i", "--input-list", help='collection/role list of the form "collection community.general"')
    parser.add_argument("-o", "--out-dir", help="path to ram subset dir")
    args = parser.parse_args()

    ram_all_dir = args.dir
    input_list = args.input_list
    out_dir = args.out_dir

    if not os.path.exists(ram_all_dir):
        raise ValueError(f"ram-all dir does not exist: {ram_all_dir}")
    
    if not os.path.exists(input_list):
        raise ValueError(f"subset list does not exist: {input_list}")
    
    sg = SubsetGenerator(ram_all_dir, out_dir)
    subset_list = sg.gen_list(input_list)
    sg.gen_subset(subset_list)
