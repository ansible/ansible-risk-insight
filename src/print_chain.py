import os
import sys
import json


def main(args):
    fpath = args[1]
    chaindata = None
    with open(fpath, "r") as file:
        chaindata = json.load(file)
    for chainsingle in chaindata:
        print("------------------------")
        ctx = chainsingle.get("context", {})
        chain = ctx.get("chain", [])
        for chain_item in chain:
            obj = chain_item.get("obj", {})
            depth = chain_item.get("depth", 0)
            indent = "  " * depth
            obj_type = obj.get("py/object", "Unknown").replace("struct4.", "")
            
            obj_name = obj.get("name", "")
            line = "{}{}: {}".format(indent, obj_type, obj_name)
            if obj_type == "Task":
                module_name = obj.get("module", "")
                line = "{}{}: {} (module: {})".format(indent, obj_type, obj_name, module_name)
            print(line)

if __name__ == "__main__":
    main(sys.argv)