import argparse
import sys
import logging
from crawl_util import crawl_root, crawl_ext, tree, resolve

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

    output_dir = args.output_dir
    collection_search_path = args.collection_dir
    skip_install = args.skip_install

    print("crawling external dependeicies")
    res_ext = crawl_ext(target, target_type, output_dir, collection_search_path, skip_install)
    # print(json.dumps(res_ext, indent=2))

    ext_index_file = res_ext.get("index_file", "")

    print("analyzing target dir")
    # root will be generated in common_data_dir
    res_root = crawl_root(target, target_type, ext_index_file, output_dir)
    # print(json.dumps(res_root, indent=2))

    root_def_dir = res_root.get("defs_dir", "")
    ext_def_dir = res_ext.get("defs_dir", "")
    index_path = res_ext.get("index_file", "")

    if root_def_dir == "" or ext_def_dir == "" or index_path == "":
        raise ValueError("Invalid input for tree anlaysis")

    out_dir = root_def_dir
    # out_dir = "/tmp/tree-tmp"

    print("analyzing inter-dependency")
    tree_path, node_path = tree(root_def_dir, ext_def_dir, index_path, out_dir)

    print("resolving")
    resolve(tree_path, node_path, out_dir)

    
