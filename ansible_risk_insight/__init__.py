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
from .scanner import ARIScanner, config


def main():
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="enable file save under ARI_DATA_DIR (default=/tmp/ari-data)",
    )
    parser.add_argument("target_type", help="Content type", choices={"project", "role", "collection"})
    parser.add_argument("target_name", help="Name")
    parser.add_argument("--install", action="store_true", help="whether to install the specified target")
    parser.add_argument("--dependency-dir", nargs="?", help="TODO")
    parser.add_argument("--source", help="source server name in ansible config file (if empty, use public ansible galaxy)")
    parser.add_argument("--pretty", action="store_true", help="show results in a pretty format")
    parser.add_argument("--without-ram", action="store_true", help="if true, RAM data is not used for this scan")
    parser.add_argument("-o", "--out-dir", help="output directory for findings")

    args = parser.parse_args()

    c = ARIScanner(
        type=args.target_type,
        name=args.target_name,
        root_dir=config.data_dir,
        dependency_dir=args.dependency_dir,
        do_save=args.save,
        without_ram=args.without_ram,
        source_repository=args.source,
        out_dir=args.out_dir,
        pretty=args.pretty,
    )
    print("Start preparing dependencies")
    c.prepare_dependencies(root_install=args.install)
    print("Start scanning")
    c.load()
