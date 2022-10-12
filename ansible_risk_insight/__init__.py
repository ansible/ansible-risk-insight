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
from .data_container import DataContainer, config


def main():
    parser = argparse.ArgumentParser(description="TODO")
    parser.add_argument(
        "-s",
        "--save",
        action="store_true",
        help="enable file save under ARI_DATA_DIR (default=/tmp/ari-data)",
    )
    parser.add_argument("target_type", help="Content type", choices={"role", "collection"})
    parser.add_argument("target_name", help="Name")
    parser.add_argument("dependency_dir", nargs="?", help="TODO")

    args = parser.parse_args()

    c = DataContainer(
        type=args.target_type,
        name=args.target_name,
        root_dir=config.data_dir,
        dependency_dir=args.dependency_dir,
        do_save=args.save,
    )
    c.load()
