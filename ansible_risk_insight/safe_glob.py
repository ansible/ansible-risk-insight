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

import os
import sys
import re


# glob.glob() may cause infinite loop when there is symlink loop
# safe_glob() support the case by `followlink=False` option as default
def safe_glob(patterns, root_dir="", recursive=True, followlinks=False):
    pattern_list = []
    if isinstance(patterns, list):
        pattern_list = [p for p in patterns]
    elif isinstance(patterns, str):
        pattern_list = [patterns]
    else:
        raise ValueError("patterns for safe_glob() must be str or list of str")

    matched_files = []
    for pattern in pattern_list:
        # if root dir is not specified, automatically decide it with pattern
        # e.g.) pattern "testdir1/testdir2/*.py"
        #       --> root_dir "testdir1/testdir2"
        root_dir_for_this_pattern = ""
        if root_dir == "":
            root_cand = pattern.split("*")[0]
            if root_cand.endswith("/"):
                root_cand = root_cand[:-1]  # trim "/" suffix
            else:
                root_cand = "/".join(root_cand.split("/")[:-1])  # testdir1/testdir2/file-*.txt --> testdir1/testdir2
            root_dir_for_this_pattern = root_cand
        else:
            root_dir_for_this_pattern = root_dir

        # if recusive, use os.walk to search files recursively
        if recursive:
            for dirpath, folders, files in os.walk(root_dir_for_this_pattern, followlinks=followlinks):
                for file in files:
                    fpath = os.path.join(dirpath, file)
                    fpath = os.path.normpath(fpath)
                    if fpath in matched_files:
                        continue
                    if pattern_match(pattern, fpath):
                        matched_files.append(fpath)
        else:
            # otherwise, just use os.listdir to avoid
            # unnecessary loading time of os.walk
            files = os.listdir(root_dir_for_this_pattern)
            for file in files:
                fpath = os.path.join(root_dir, file)
                fpath = os.path.normpath(fpath)
                if fpath in matched_files:
                    continue
                if pattern_match(pattern, fpath):
                    matched_files.append(fpath)
    return matched_files


def pattern_match(pattern, fpath):
    pattern = pattern.replace("**/", "<ANY>")
    pattern = pattern.replace("*", "[^/]*")
    pattern = pattern.replace("<ANY>", ".*")
    regex_pattern = r"^{}$".format(pattern)
    return re.match(regex_pattern, fpath)


if __name__ == "__main__":
    dir, pattern = sys.argv[1], sys.argv[2]
    found = safe_glob(dir, [pattern], recursive=False)
    print(found)
