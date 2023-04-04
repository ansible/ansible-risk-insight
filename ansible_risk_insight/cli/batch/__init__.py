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

import traceback
import os
import joblib
import argparse
from ...scanner import ARIScanner, config


class BatchCLI:
    args = None
    _scanner = None

    def __init__(self):
        parser = argparse.ArgumentParser(description="TODO")
        parser.add_argument(
            "-s",
            "--save",
            action="store_true",
            help="enable file save under ARI_DATA_DIR (default=/tmp/ari-data)",
        )
        parser.add_argument("-f", "--file", help='target list like "collection community.general"')
        parser.add_argument("--include-tests", action="store_true", help='if true, load test contents in "tests/integration/targets"')
        parser.add_argument("--objects", action="store_true", help="if true, output objects.json to the output directory")
        parser.add_argument("--serial", action="store_true", help="if true, do not parallelize ram generation")
        parser.add_argument("-o", "--out-dir", help="output directory for the rule evaluation result")
        parser.add_argument(
            "-r", "--rules-dir", help=f"specify custom rule directories. use `-R` instead to ignore default rules in {config.rules_dir}"
        )
        parser.add_argument("-R", "--rules-dir-without-default", help="specify custom rule directories and ignore default rules")
        args = parser.parse_args()
        self.args = args

        use_ansible_doc = True

        read_ram = True
        write_ram = True
        if args.include_tests:
            read_ram = False
            write_ram = False

        self._scanner = ARIScanner(
            root_dir=config.data_dir,
            silent=True,
            use_ansible_doc=use_ansible_doc,
            persist_dependency_cache=True,
            read_ram=read_ram,
            write_ram=write_ram,
        )

    def run(self):
        args = self.args

        target_list = []
        with open(args.file, "r") as file:
            for line in file:
                parts = line.replace("\n", "").split(" ")
                if len(parts) != 2:
                    raise ValueError('target list file must be lines of "<type> <name>" such as "collection community.general"')
                target_list.append((parts[0], parts[1]))
        num = len(target_list)

        input_list = []
        for i, target_info in enumerate(target_list):
            if not isinstance(target_info, tuple):
                raise ValueError(f"target list must be a list of tuple(target_type, target_name), but got a {type(target_info)}")
            if len(target_info) != 2:
                raise ValueError(f"target list must be a list of tuple(target_type, target_name), but got this; {target_info}")

            _type, _name = target_info
            input_list.append((i, num, _type, _name))

        parallel = True
        if args.serial:
            parallel = False

        if parallel:
            joblib.Parallel(n_jobs=-1)(joblib.delayed(self.scan)(i, num, _type, _name) for (i, num, _type, _name) in input_list)
        else:
            for (i, num, _type, _name) in input_list:
                self.scan(i, num, _type, _name)

    def scan(self, i, num, type, name):
        args = self.args
        print(f"[{i+1}/{num}] {type} {name}")
        use_src_cache = True

        try:
            out_dir = None
            if args.out_dir:
                out_dir = os.path.join(args.out_dir, type, name)
            self._scanner.evaluate(
                type=type,
                name=name,
                install_dependencies=True,
                include_test_contents=args.include_tests,
                use_src_cache=use_src_cache,
                out_dir=out_dir,
            )
        except Exception:
            error = traceback.format_exc()
            self._scanner.save_error(error)
