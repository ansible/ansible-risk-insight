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
        parser.add_argument("target_type", help="Content type", choices={"project", "role", "collection", "playbook", "taskfile"})
        parser.add_argument("target_name", help="Name")
        parser.add_argument("--playbook-only", action="store_true", help="if true, don't load playbooks/roles arround the specified playbook")
        parser.add_argument("--taskfile-only", action="store_true", help="if true, don't load playbooks/roles arround the specified taskfile")
        parser.add_argument("--skip-install", action="store_true", help="if true, skip install for the specified target")
        parser.add_argument("--dependency-dir", nargs="?", help="path to a directory that have dependencies for the target")
        parser.add_argument("--collection-name", nargs="?", help="if provided, use it as a collection name")
        parser.add_argument("--role-name", nargs="?", help="if provided, use it as a role name")
        parser.add_argument("--source", help="source server name in ansible config file (if empty, use public ansible galaxy)")
        parser.add_argument("--without-ram", action="store_true", help="if true, RAM data is not used and not even updated")
        parser.add_argument("--read-only-ram", action="store_true", help="if true, RAM data is used but not updated")
        parser.add_argument("--read-ram-for-dependency", action="store_true", help="if true, RAM data is used only for dependency")
        parser.add_argument("--update-ram", action="store_true", help="if true, RAM data is not used for scan but updated with the scan result")
        parser.add_argument("--include-tests", action="store_true", help='if true, load test contents in "tests/integration/targets"')
        parser.add_argument("--silent", action="store_true", help='if true, do not print anything"')
        parser.add_argument("--objects", action="store_true", help="if true, output objects.json to the output directory")
        parser.add_argument("--show-all", action="store_true", help="if true, show findings even if missing dependencies are found")
        parser.add_argument("--json", help="if specified, show findings in json format")
        parser.add_argument("--yaml", help="if specified, show findings in yaml format")
        parser.add_argument("-o", "--out-dir", help="output directory for the rule evaluation result")
        parser.add_argument(
            "-r", "--rules-dir", help=f"specify custom rule directories. use `-R` instead to ignore default rules in {config.rules_dir}"
        )
        parser.add_argument("-R", "--rules-dir-without-default", help="specify custom rule directories and ignore default rules")
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
        if args.target_type in ["project", "playbook", "taskfile"] and not is_url(target_name):
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

        rules_dir = config.rules_dir
        if args.rules_dir_without_default:
            rules_dir = args.rules_dir_without_default
        elif args.rules_dir:
            rules_dir = args.rules_dir + ":" + config.rules_dir

        silent = args.silent
        pretty = False
        output_format = ""
        if args.json or args.yaml:
            silent = True
            pretty = True
            if args.json:
                output_format = "json"
            elif args.yaml:
                output_format = "yaml"

        read_ram = True
        write_ram = True
        read_ram_for_dependency = False
        if args.without_ram:
            read_ram = False
            write_ram = False
        elif args.read_only_ram:
            read_ram = True
            write_ram = False
        elif args.update_ram:
            read_ram = False
            write_ram = True
        elif args.read_ram_for_dependency:
            read_ram_for_dependency = True
            read_ram = False
            write_ram = False
        elif args.include_tests:
            read_ram_for_dependency = True
            read_ram = False
            write_ram = False

        c = ARIScanner(
            root_dir=config.data_dir,
            rules_dir=rules_dir,
            do_save=args.save,
            read_ram=read_ram,
            write_ram=write_ram,
            read_ram_for_dependency=read_ram_for_dependency,
            show_all=args.show_all,
            silent=silent,
            pretty=pretty,
            output_format=output_format,
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
            playbook_only=args.playbook_only,
            taskfile_only=args.taskfile_only,
            include_test_contents=args.include_tests,
            objects=args.objects,
            out_dir=args.out_dir,
        )
