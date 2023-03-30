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

key_delimiter = ":"
object_delimiter = "#"


class Key:
    def __init__(self, str):
        self.key = str

    def detect_type(self):
        return self.key.split(" ")[0]

    # convert key to tree root name
    def to_name(self):
        _type = self.detect_type()
        if _type == "playbook":
            return os.path.basename(self.key.split(key_delimiter)[-1])
        elif _type == "role":
            return self.key.split(key_delimiter)[-1]


def make_global_key_prefix(collection, role):
    key_prefix = ""
    if collection != "":
        key_prefix = "collection{}{}{}".format(key_delimiter, collection, object_delimiter)
    elif role != "":
        key_prefix = "role{}{}{}".format(key_delimiter, role, object_delimiter)
    return key_prefix


def detect_type(key=""):
    return key.split(" ")[0]


def set_play_key(obj, parent_key="", parent_local_key=""):
    type_str = obj.type
    index_info = "[{}]".format(obj.index)
    _parent_key = parent_key.split(" ")[-1]
    _parent_local_key = parent_local_key.split(" ")[-1]
    global_key = "{} {}{}{}{}{}".format(
        type_str,
        _parent_key,
        object_delimiter,
        type_str,
        key_delimiter,
        index_info,
    )
    local_key = "{} {}{}{}{}{}".format(
        type_str,
        _parent_local_key,
        object_delimiter,
        type_str,
        key_delimiter,
        index_info,
    )
    obj.key = global_key
    obj.local_key = local_key


def set_role_key(obj):
    global_key_prefix = make_global_key_prefix(obj.collection, "")
    global_key = "{} {}{}{}{}".format(obj.type, global_key_prefix, obj.type, key_delimiter, obj.fqcn)
    local_key = "{} {}{}{}".format(obj.type, obj.type, key_delimiter, obj.defined_in)
    obj.key = global_key
    obj.local_key = local_key


def set_module_key(obj):
    global_key_prefix = make_global_key_prefix(obj.collection, obj.role)
    global_key = "{} {}{}{}{}".format(obj.type, global_key_prefix, obj.type, key_delimiter, obj.fqcn)
    local_key = "{} {}{}{}".format(obj.type, obj.type, key_delimiter, obj.defined_in)
    obj.key = global_key
    obj.local_key = local_key


def set_collection_key(obj):
    global_key = "{} {}{}{}".format(obj.type, obj.type, key_delimiter, obj.name)
    local_key = global_key
    obj.key = global_key
    obj.local_key = local_key


def get_obj_type(key):
    idx0 = key.find(" ")
    obj_type = key[:idx0]
    if obj_type in [
        "module",
        "play",
        "playbook",
        "role",
        "collection",
        "task",
        "taskfile",
        "repository",
    ]:
        return obj_type
    else:
        return None


def get_obj_info_by_key(key):
    info = {}
    info["key"] = key
    skip = False

    idx0 = key.find(" ")
    obj_type = key[:idx0]
    info["type"] = obj_type
    skip = idx0 < 0
    if not skip:
        s1 = key[idx0 + 1 :]
        if obj_type == "task" or obj_type == "play":
            idx1 = s1.find(object_delimiter)
            parent_key = s1[:idx1]
            info["parent_key"] = parent_key
            sidx1 = parent_key.find(":")
            parent_type = parent_key[:sidx1]
            info["parent_type"] = parent_type
            parent_name = parent_key[sidx1 + 1 :]
            info["parent_name"] = parent_name
            skip = skip or idx1 < 0
            if not skip:
                s2 = s1[idx1 + 1 :]
                idx2 = s2.find(key_delimiter)
                obj_type = s2[:idx2]
                info["obj_type"] = obj_type
                skip = skip or idx2 < 0
            if not skip:
                obj_key = s2[idx2 + 1 :]
                info["obj_key"] = obj_key
        elif obj_type == "taskfile" or obj_type == "playbook":
            idx1 = s1.find(key_delimiter)
            skip = skip or idx1 < 0
            if not skip:
                parent_type = s1[:idx1]
                info["parent_type"] = parent_type
                s2 = s1[idx1 + 1 :]
                idx2 = s2.find(object_delimiter)
                skip = skip or idx2 < 0
            if not skip:
                parent_name = s2[:idx2]
                info["parent_name"] = parent_name
                s3 = s2[idx2 + 1 :]
                idx3 = s3.find(key_delimiter)
                skip = skip or idx3 < 0
            if not skip:
                defined_in = s3[idx3 + 1 :]
                info["defined_in"] = defined_in
        elif obj_type == "role" or obj_type == "module":
            idx1 = s1.find(key_delimiter)
            parent_type = s1[:idx1]
            info["parent_type"] = parent_type
            skip = skip or idx1 < 0
            if not skip:
                s2 = s1[idx1 + 1 :]
                idx2 = s2.find(object_delimiter)
                parent_name = s2[:idx2]
                info["parent_name"] = parent_name
                skip = skip or idx2 < 0
            if not skip:
                s3 = s2[idx2 + 1 :]
                idx3 = s3.find(key_delimiter)
                skip = skip or idx3 < 0
            if not skip:
                fqcn = s3[idx3 + 1 :]
                info["fqcn"] = fqcn
        elif obj_type == "collection" or obj_type == "repository":
            idx1 = s1.find(key_delimiter)
            skip = skip or idx1 < 0
            if not skip:
                name = s1[idx1 + 1 :]
                info["name"] = name
        else:
            pass

    return info


def set_task_key(obj, parent_key="", parent_local_key=""):
    index_info = "[{}]".format(obj.index)
    _parent_key = parent_key.split(" ")[-1]
    _parent_local_key = parent_local_key.split(" ")[-1]
    global_key = "{} {}{}{}{}{}".format(
        obj.type,
        _parent_key,
        object_delimiter,
        obj.type,
        key_delimiter,
        index_info,
    )
    local_key = "{} {}{}{}{}{}".format(
        obj.type,
        _parent_local_key,
        object_delimiter,
        obj.type,
        key_delimiter,
        index_info,
    )
    obj.key = global_key
    obj.local_key = local_key


def set_taskfile_key(obj):
    global_key_prefix = make_global_key_prefix(obj.collection, obj.role)
    global_key = "{} {}{}{}{}".format(
        obj.type,
        global_key_prefix,
        obj.type,
        key_delimiter,
        obj.defined_in,
    )
    local_key = "{} {}{}{}".format(obj.type, obj.type, key_delimiter, obj.defined_in)
    obj.key = global_key
    obj.local_key = local_key


def set_playbook_key(obj):
    global_key_prefix = make_global_key_prefix(obj.collection, obj.role)
    global_key = "{} {}{}{}{}".format(
        obj.type,
        global_key_prefix,
        obj.type,
        key_delimiter,
        obj.defined_in,
    )
    local_key = "{} {}{}{}".format(obj.type, obj.type, key_delimiter, obj.defined_in)
    obj.key = global_key
    obj.local_key = local_key


def set_repository_key(obj):
    global_key = "{} {}{}{}".format(obj.type, obj.type, key_delimiter, obj.name)
    local_key = global_key
    obj.key = global_key
    obj.local_key = local_key


def set_call_object_key(cls_name: str, spec_key: str, caller_key: str):
    parts = spec_key.split(" ", 1)
    caller_only = caller_key.split(" FROM ")[0]
    return "{} {} FROM {}".format(cls_name, parts[1], caller_only)


def make_imported_taskfile_key(caller_key, path):
    caller_key_payload = caller_key.split(" ")[-1]
    parts = caller_key_payload.split(object_delimiter)
    parent = ""
    if parts[0].startswith(("collection", "role")):
        parent = parts[0] + object_delimiter
    normed_path = os.path.normpath(path)
    key = f"taskfile {parent}taskfile{key_delimiter}{normed_path}"
    return key
