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

import codecs
import os
import re


valid_playbook_re = re.compile(r"^\s*?-?\s*?(?:hosts|include|import_playbook):\s*?.*?$")


# this method is based on awx code
# awx/main/utils/ansible.py#L42-L64 in ansible/awx
def could_be_playbook(fpath):
    basename, ext = os.path.splitext(fpath)
    if ext not in [".yml", ".yaml"]:
        return False
    # Filter files that do not have either hosts or top-level
    # includes. Use regex to allow files with invalid YAML to
    # show up.
    matched = False
    try:
        with codecs.open(fpath, "r", encoding="utf-8", errors="ignore") as f:
            for n, line in enumerate(f):
                if valid_playbook_re.match(line):
                    matched = True
                    break
                # Any YAML file can also be encrypted with vault;
                # allow these to be used as the main playbook.
                elif n == 0 and line.startswith("$ANSIBLE_VAULT;"):
                    matched = True
                    break
    except IOError:
        return False
    return matched


def could_be_taskfile(fpath):
    if could_be_playbook(fpath):
        return False
    with codecs.open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        for n, line in enumerate(f):
            if "- name: " in line:
                return True
            if "ansible.builtin." in line:
                return True
    return False


# this method is based on awx code
# awx/main/models/projects.py#L206-L217 in ansible/awx
def search_playbooks(root_path):
    results = []
    if root_path and os.path.exists(root_path):
        for dirpath, dirnames, filenames in os.walk(root_path, followlinks=False):
            if skip_directory(dirpath):
                continue
            for filename in filenames:
                fpath = os.path.join(dirpath, filename)
                if could_be_playbook(fpath):
                    results.append(fpath)
    return sorted(results, key=lambda x: x.lower())


# this method is based on awx code
# awx/main/utils/ansible.py#L24-L39 in ansible/awx
def skip_directory(relative_directory_path):
    path_elements = relative_directory_path.split(os.sep)
    # Exclude files in a roles subdirectory.
    if "roles" in path_elements:
        return True
    # Filter files in a tasks subdirectory.
    if "tasks" in path_elements:
        return True
    for element in path_elements:
        # Do not include dot files or dirs
        if element.startswith("."):
            return True
    # Exclude anything inside of group or host vars directories
    if "group_vars" in path_elements or "host_vars" in path_elements:
        return True
    return False
