import os
import glob
import argparse
import shutil


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
    
    # find findings.json from ram-all dir
    for _type, _name in subset_list:
        files = []
        if _type == "collection":
            files = glob.glob(f"{ram_all_dir}/collections/findings/{_name}/**/findings.json", recursive=True)
        elif _type == "role":
            files = glob.glob(f"{ram_all_dir}/roles/findings/{_name}/**/findings.json", recursive=True)

        if len(files) == 0:
            print(f"findings.json not found. ({_type} {_name})")
            continue
        for f_json in files:
            relative_path = f_json.replace(ram_all_dir, "").strip("/")
            dest_path = os.path.join(out_dir, relative_path)
            dest_dir = os.path.dirname(dest_path)
            os.makedirs(dest_dir, exist_ok=True)
            shutil.copy2(f_json, dest_path)