import argparse
import sys
import logging
from crawl_util import crawl_root, crawl_ext, tree

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='crawl.py',
        description='crawl a collection/role, and store data under a common directory',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-r', '--role', default="", help='role name')
    parser.add_argument('-c', '--collection', default="", help='collection name')
    parser.add_argument('-o', '--output-dir', default="", help='path to the output directory')
    parser.add_argument('--collection-dir', default="", help='path to the collection directory (for dependencies of role)')
    parser.add_argument('-s', '--skip-install', action='store_true', help='skip ansible-galaxy install')

    args = parser.parse_args()


    if not args.output_dir:
        logging.error("output dir must be specified")
        sys.exit(1)

    target = ""
    target_type = ""
    if args.collection:
        if args.role:
            logging.error("either collection or role must be specified")
            sys.exit(1)
        target_type = "collection"
        target = args.collection
    elif args.role:
        target_type = "role"
        target = args.role
    else:
        logging.error("collection or role must be specified")
        sys.exit(1)

    common_data_dir = args.output_dir
    collecion_data_dir = args.collection_dir
    skip_install = args.skip_install

    print("crawling external dependeicies")
    res_ext = crawl_ext(target, target_type, common_data_dir, collecion_data_dir, skip_install)
    # print(json.dumps(res_ext, indent=2))

    print("analyzing target dir")
    res_root = crawl_root(target, target_type, common_data_dir)
    # print(json.dumps(res_root, indent=2))

    root_def_dir = res_root.get("defs_dir", "")
    ext_def_dir = res_ext.get("defs_dir", "")
    index_path = res_ext.get("index_file", "")

    if root_def_dir == "" or ext_def_dir == "" or index_path == "":
        raise ValueError("Invalid input for tree anlaysis")

    out_dir = root_def_dir
    # out_dir = "/tmp/tree-tmp"

    print("analyzing inter-dependency")
    tree(root_def_dir, ext_def_dir, index_path, out_dir)
