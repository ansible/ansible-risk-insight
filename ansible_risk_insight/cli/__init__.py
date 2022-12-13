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
from ..utils import is_url, split_name_and_version


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
        parser.add_argument("target_type", help="Content type", choices={"project", "role", "collection"})
        parser.add_argument("target_name", help="Name")
        parser.add_argument("--skip-install", action="store_true", help="if true, skip install for the specified target")
        parser.add_argument("--dependency-dir", nargs="?", help="path to a directory that have dependencies for the target")
        parser.add_argument("--collection-name", nargs="?", help="if provided, use it as a collection name of the project repository")
        parser.add_argument("--source", help="source server name in ansible config file (if empty, use public ansible galaxy)")
        parser.add_argument("--pretty", action="store_true", help="show results in a pretty format")
        parser.add_argument("--without-ram", action="store_true", help="if true, RAM data is not used for this scan")
        parser.add_argument("--show-all", action="store_true", help="if true, show findings even if missing dependencies are found")
        parser.add_argument("-o", "--out-dir", help="output directory for findings")
        args = parser.parse_args()
        self.args = args

    def run(self):
        args = self.args
        target_name = args.target_name
        target_version = ""
        if args.target_type in ["collection", "role"]:
            target_name, target_version = split_name_and_version(target_name)

        collection_name_of_project = ""
        if args.target_type == "project":
            if args.collection_name:
                collection_name_of_project = args.collection_name
            else:
                if is_url(target_name):
                    pass
                else:
                    last_part = target_name.split("/")[-1]
                    if len(last_part.split(".")) == 2:
                        collection_name_of_project = last_part

        c = ARIScanner(
            type=args.target_type,
            name=target_name,
            version=target_version,
            root_dir=config.data_dir,
            dependency_dir=args.dependency_dir,
            collection_name=collection_name_of_project,
            do_save=args.save,
            without_ram=args.without_ram,
            source_repository=args.source,
            out_dir=args.out_dir,
            show_all=args.show_all,
            pretty=args.pretty,
        )
        print("Start preparing dependencies")
        root_install = not args.skip_install
        c.prepare_dependencies(root_install=root_install)
        print("Start scanning")
        c.load()
