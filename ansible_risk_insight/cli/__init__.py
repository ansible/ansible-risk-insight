# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2022 IBM Corp. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse

from ..scanner import ARIScanner, config
from ..utils import (
    is_url,
    is_local_path,
    get_collection_metadata,
    get_role_metadata,
    split_name_and_version,
)


class ARICLI:
    args = None

    def __init__(self):
        parser = argparse.ArgumentParser(description="TODO")
        parser.add_argument(
            "-s",
            "--save",
            action="store_true",
            help="enable file save under ARI_DATA_DIR (default=/tmp/ari-data)",
        )
        parser.add_argument("target_type", help="Content type", choices={"project", "role", "collection", "playbook"})
        parser.add_argument("target_name", help="Name")
        parser.add_argument("--skip-install", action="store_true", help="if true, skip install for the specified target")
        parser.add_argument("--dependency-dir", nargs="?", help="path to a directory that have dependencies for the target")
        parser.add_argument("--collection-name", nargs="?", help="if provided, use it as a collection name")
        parser.add_argument("--role-name", nargs="?", help="if provided, use it as a role name")
        parser.add_argument("--source", help="source server name in ansible config file (if empty, use public ansible galaxy)")
        parser.add_argument("--without-ram", action="store_true", help="if true, RAM data is not used and not even updated")
        parser.add_argument("--update-ram", action="store_true", help="if true, RAM data is not used for scan but updated with the scan result")
        parser.add_argument("--show-all", action="store_true", help="if true, show findings even if missing dependencies are found")
        parser.add_argument("-o", "--output", help="if specified, show findings in json/yaml format", choices={"json", "yaml"})
        parser.add_argument("--out-dir", help="output directory for findings")
        args = parser.parse_args()
        self.args = args

    def run(self):
        args = self.args
        target_name = args.target_name
        target_version = ""
        if args.target_type in ["collection", "role"]:
            target_name, target_version = split_name_and_version(target_name)

        collection_name = ""
        role_name = ""
        if args.collection_name:
            collection_name = args.collection_name

        if args.role_name:
            role_name = args.role_name

        is_local = False
        if args.target_type in ["collection", "role"] and is_local_path(target_name):
            is_local = True
        if args.target_type in ["project", "playbook"] and not is_url(target_name):
            is_local = True

        if is_local and not collection_name and not role_name:
            coll_meta = get_collection_metadata(target_name)
            if coll_meta:
                _namespace = coll_meta.get("collection_info", {}).get("namespace", "")
                _name = coll_meta.get("collection_info", {}).get("name", "")
                collection_name = f"{_namespace}.{_name}"

            role_meta = get_role_metadata(target_name)
            if role_meta:
                role_name = role_meta.get("galaxy_info", {}).get("role_name", "")

        silent = False
        pretty = False
        if args.output:
            silent = True
            pretty = True

        read_ram = True
        write_ram = True
        if args.without_ram:
            read_ram = False
            write_ram = False
        elif args.update_ram:
            read_ram = False
            write_ram = True

        c = ARIScanner(
            root_dir=config.data_dir,
            do_save=args.save,
            read_ram=read_ram,
            write_ram=write_ram,
            show_all=args.show_all,
            silent=silent,
            pretty=pretty,
            output_format=args.output,
        )
        if not silent and not pretty:
            print("Start preparing dependencies")
        root_install = not args.skip_install
        if not silent and not pretty:
            print("Start scanning")
        c.evaluate(
            type=args.target_type,
            name=target_name,
            version=target_version,
            install_dependencies=root_install,
            dependency_dir=args.dependency_dir,
            collection_name=collection_name,
            role_name=role_name,
            source_repository=args.source,
            out_dir=args.out_dir,
        )
