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
        key_prefix = "collection{}{}{}".format(
            key_delimiter, collection, object_delimiter
        )
    elif role != "":
        key_prefix = "role{}{}{}".format(
            key_delimiter, role, object_delimiter
        )
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
    global_key = "{} {}{}{}{}".format(
        obj.type, global_key_prefix, obj.type, key_delimiter, obj.fqcn.lower()
    )
    local_key = "{} {}{}{}".format(
        obj.type, obj.type, key_delimiter, obj.defined_in.lower()
    )
    obj.key = global_key
    obj.local_key = local_key


def set_module_key(obj):
    global_key_prefix = make_global_key_prefix(obj.collection, obj.role)
    global_key = "{} {}{}{}{}".format(
        obj.type, global_key_prefix, obj.type, key_delimiter, obj.fqcn.lower()
    )
    local_key = "{} {}{}{}".format(
        obj.type, obj.type, key_delimiter, obj.defined_in.lower()
    )
    obj.key = global_key
    obj.local_key = local_key


def set_collection_key(obj):
    global_key = "{} {}{}{}".format(
        obj.type, obj.type, key_delimiter, obj.name.lower()
    )
    local_key = global_key
    obj.key = global_key
    obj.local_key = local_key

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
        obj.defined_in.lower(),
    )
    local_key = "{} {}{}{}".format(
        obj.type, obj.type, key_delimiter, obj.defined_in.lower()
    )
    obj.key = global_key
    obj.local_key = local_key


def set_playbook_key(obj):
    global_key_prefix = make_global_key_prefix(obj.collection, obj.role)
    global_key = "{} {}{}{}{}".format(
        obj.type,
        global_key_prefix,
        obj.type,
        key_delimiter,
        obj.defined_in.lower(),
    )
    local_key = "{} {}{}{}".format(
        obj.type, obj.type, key_delimiter, obj.defined_in.lower()
    )
    obj.key = global_key
    obj.local_key = local_key


def set_repository_key(obj):
    global_key = "{} {}{}{}".format(
        obj.type, obj.type, key_delimiter, obj.name.lower()
    )
    local_key = global_key
    obj.key = global_key
    obj.local_key = local_key
