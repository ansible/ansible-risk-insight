import argparse
import os
import sys
import json
import jsonpickle
import logging
from struct5 import ObjectList, detect_type, ExecutableType
from tree import TreeNode, key_to_file_name, load_node_objects, TreeLoader, TreeNode, load_all_definitions
from context import Context, resolve_module_options

def convert(tree, node_objects):
    node_dict = {}
    inbound_counter = 0
    cmd_counter = 0
    install_counter = 0
    file_counter = 0
    network_counter = 0
    system_counter = 0
    total_counter = 0

    for no in node_objects.items:
        node_dict[no.key] = no

    def getSubTree(node, root=False):
        obj = {}
        no = node_dict[node.key]
        node_type = detect_type(node.key)

        # define here
        obj["type"] = node_type
        if root:
            obj["path"] = no.defined_in

        if node_type == "module":
            obj["fqcn"] = no.fqcn
        else:
            if "name" in obj:
                obj["name"] = no.name

            if node_type == "task":
                obj["name"] = no.name
                # obj["obj"] = no.__dict__

                if no.executable_type == ExecutableType.MODULE_TYPE:
                    obj["resolved_name"] = no.resolved_name

            children_per_type = {}
            for c in node.children:
                ctype = detect_type(c.key)
                if ctype in children_per_type:
                    children_per_type[ctype].append(c)
                else:
                    children_per_type[ctype] = [c]

            #obj["children_types"] = list(children_per_type.keys())
            if "playbook" in children_per_type:
                obj["playbooks"] = [ getSubTree(c) for c in children_per_type["playbook"] ]
            if "play" in children_per_type:
                obj["plays"] = [ getSubTree(c) for c in children_per_type["play"] ]
            if "role" in children_per_type:
                obj["roles"] = [ getSubTree(c) for c in children_per_type["role"]]
            if "taskfile" in children_per_type:
                obj["taskfiles"] = [ getSubTree(c) for c in children_per_type["taskfile"]]
            if "task" in children_per_type:
                obj["tasks"] = [ getSubTree(c) for c in children_per_type["task"]]
            if "module" in children_per_type:
                tmp_children = [getSubTree(c) for c in children_per_type["module"]]
                resolved_name = tmp_children[0]["fqcn"] if len(tmp_children) > 0 else ""
                obj["resolved_name"] = resolved_name
                obj["module_options"] = no.module_options

                cmd_modules = ["ansible.builtin.command","ansible.builtin.shell"]
                install_modules = ["ansible.builtin.package","community.general.homebrew","ansible.builtin.pip"]
                inbound_modules = ["ansible.builtin.get_url","ansible.builtin.fetch"]
                file_change_modules = ["ansible.builtin.lineinfile", "ansible.builtin.file",\
                    "ansible.builtin.template", "ansible.builtin.replace", "community.crypto.openssh_keypair"]
                system_change_modules = ["community.libvirt.virt_pool","community.libvirt.virt_net",\
                    "community.libvirt.virt", "ansible.builtin.service","community.general.lvol","ansible.posix.mount"]
                network_change_modules = ["ansible.posix.firewalld","community.general.seport"]

                nonlocal total_counter
                total_counter += 1
                if resolved_name in cmd_modules:
                    obj["findings"] = "cmd execution"
                    nonlocal cmd_counter
                    cmd_counter += 1
                if resolved_name in install_modules:
                    obj["findings"] = "package installation"
                    nonlocal install_counter
                    install_counter += 1
                if resolved_name in inbound_modules:
                    obj["findings"] = "inbound"
                    nonlocal inbound_counter
                    inbound_counter += 1
                if resolved_name in file_change_modules:
                    obj["findings"] = "file change"
                    nonlocal file_counter
                    file_counter += 1
                if resolved_name in system_change_modules:
                    obj["findings"] = "system change"
                    nonlocal system_counter
                    system_counter += 1
                if resolved_name in network_change_modules:
                    obj["findings"] = "network change"
                    nonlocal network_counter
                    network_counter += 1

                # findings = {}
                # labels = []
                # label_cmd = "command execution"
                # label_file = "file change"
                # label_cfg = "configration change"
                # label_svc = "manage service"
                # label_install = "package installation"
                # label_transfer = "inbound data transfer"
                # label_libvirt = "manage virtual machines"
                # label_network = "manage network configuration"
                # label_ibmz = "manage resources on IBM Z"
                # label_key = "manage key"
                # label_port = "port open"
                # label_rhel = "manage registration to Red Hat Subscription Manager"
                # label_vol = "manage volume"
                # label_action = "ansible action execution"

                # # obj["findings"] = findings
                # if resolved_name == "ansible.builtin.command":
                #     findings["command"] = no.module_options
                #     labels.append(label_cmd)
                # elif resolved_name == "ansible.builtin.shell":
                #     findings["shell"] = no.module_options
                #     labels.append(label_cmd)
                # elif resolved_name == "ansible.builtin.lineinfile":
                #     findings["lineinfile"] = no.module_options
                #     labels.append(label_file)
                # elif resolved_name == "ansible.builtin.file":
                #     findings["file"] = no.module_options
                #     labels.append(label_file)                    
                # elif resolved_name == "ansible.builtin.template":
                #     findings["template"] = no.module_options
                #     labels.append(label_file)
                # elif resolved_name == "ansible.builtin.service":
                #     findings["service"] = no.module_options
                #     labels.append(label_svc)         
                # elif resolved_name == "ansible.builtin.package":
                #     findings["package"] = no.module_options["name"]
                #     labels.append(label_install)      
                # elif resolved_name == "community.libvirt.virt_pool":
                #     findings["virt_pool"] = no.module_options
                #     labels.append(label_libvirt)     
                # elif resolved_name == "community.libvirt.virt_net":
                #     findings["virt_net"] = no.module_options
                #     labels.append(label_libvirt)   
                #     labels.append(label_network)
                # elif resolved_name == "ansible.builtin.replace":
                #     findings["replace"] = no.module_options
                #     labels.append(label_file) 
                # elif resolved_name == "ansible.builtin.get_url":
                #     findings["get_url"] = no.module_options
                #     labels.append(label_install)  
                #     labels.append(label_transfer)  
                # elif resolved_name == "community.libvirt.virt":
                #     findings["virt"] = no.module_options
                #     labels.append(label_libvirt)   
                # # elif resolved_name == "ibm.ibm_zhmc.zhmc_storage_group_attachment": # ensure ...
                # #     findings["zhmc_storage_group_attachment"] = no.module_options
                # #     labels.append(label_ibmz)   
                # elif resolved_name == "ibm.ibm_zhmc.zhmc_partition":
                #     findings["zhmc_partition"] = no.module_options
                #     labels.append(label_ibmz)  
                # # elif resolved_name == "ibm.ibm_zhmc.zhmc_nic": # ensure ...
                # #     findings["zhmc_nic"] = no.module_options
                # #     labels.append(label_ibmz)   
                # elif resolved_name == "community.general.selinux_permissive": #change permissive domain
                #     findings["selinux_permissive"] = no.module_options
                #     labels.append(label_cfg)   
                # elif resolved_name == "community.general.homebrew":
                #     findings["homebrew"] = no.module_options
                #     labels.append(label_install)   
                #     labels.append(label_transfer) 
                # elif resolved_name == "community.crypto.openssh_keypair":
                #     findings["openssh_keypair"] = no.module_options
                #     labels.append(label_key)   
                # elif resolved_name == "ansible.posix.firewalld":
                #     findings["firewalld"] = no.module_options
                #     labels.append(label_network)   
                #     labels.append(label_port) 
                # elif resolved_name == "community.general.redhat_subscription":
                #     findings["redhat_subscription"] = no.module_options
                #     labels.append(label_rhel)   
                # elif resolved_name == "community.general.seport":
                #     findings["seport"] = no.module_options
                #     labels.append(label_network)   
                #     labels.append(label_port) 
                # elif resolved_name == "community.general.lvol":
                #     findings["lvol"] = no.module_options
                #     labels.append(label_vol)   
                # elif resolved_name == "ansible.builtin.rpm_key":
                #     findings["rpm_key"] = no.module_options
                #     labels.append(label_key)   
                # elif resolved_name == "ansible.builtin.meta":
                #     findings["meta"] = no.module_options
                #     labels.append(label_action)   
                # elif resolved_name == "ansible.posix.mount":
                #     findings["mount"] = no.module_options
                #     labels.append(label_cfg)   
                # elif resolved_name == "ansible.builtin.pip":
                #     findings["pip"] = no.module_options["requirements"]
                #     labels.append(label_install) 
                #     labels.append(label_transfer)   
                # elif resolved_name == "ansible.builtin.fetch":
                #     findings["fetch"] = no.module_options
                #     labels.append(label_transfer)   
                # obj["labels"] = labels

        # end
        return obj

    tObj = getSubTree(tree, root=True)
    tObj["dependent_collections"] = list(set([ no.collection for no in node_objects.items if hasattr(no, "collection") and no.collection != ""]))
    tObj["dependent_roles"] = list(set([ no.role for no in node_objects.items if hasattr(no, "collection") and hasattr(no, "role") and no.collection == "" and no.role != ""]))
    tObj["dependent_module_collections"] = list(set([ no.collection for no in node_objects.items if detect_type(no.key)=="module" and hasattr(no, "collection") and no.collection != ""]))
    # tObj["dependent_module_roles"] = list(set([ no["role"] for no in node_objects if detect_type(no["key"])=="Module" and "collection" not in no]))
    tObj["module_calls"] = {"total": total_counter, "inbound_data_transfer": inbound_counter, "cmd_exec": cmd_counter, \
        "install": install_counter, "file_change": file_counter, "network_change": network_counter, "system_change": system_counter}

    context_and_task = []
    def add_context(node, context=None, depth_level=0):
        current_context = None
        if context is None:
            current_context = Context()
        else:
            current_context = context.copy()
        node_type = detect_type(node.key)
        obj = node_dict[node.key]
        current_context.add(obj, depth_level)
        if node_type == "Task":
            context_and_task.append((current_context, obj))

        for c in node.children:
            add_context(c, current_context, depth_level+1)
    
    add_context(tree)

    contexts = []
    for (ctx, task) in context_and_task:
        resolved_options = resolve_module_options(ctx, task)
        single_item = {
            "context": ctx,
            "task": task,
            "resolved_options": resolved_options,
        }
        contexts.append(single_item)

    return tObj, contexts

def load_tree_json(tree_path):
    trees = []
    with open(tree_path, "r") as file:
        for line in file:
            d = json.loads(line)
            src_dst_array = d.get("tree", [])
            tree = TreeNode.load(graph=src_dst_array)
            trees.append(tree)
    return trees

def load_node_objects(node_path="", root_dir="", ext_dir=""):
    objects = ObjectList()
    if node_path != "":
        objects.from_json(fpath=node_path)
    else:
        root_defs = load_all_definitions(root_dir)
        ext_defs = load_all_definitions(ext_dir)
        for type_key in root_defs:
            objects.merge(root_defs[type_key])
            objects.merge(ext_defs[type_key])
    return objects

def main():
    parser = argparse.ArgumentParser(
        prog='converter1.py',
        description='converter1',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('-t', '--tree-file', default="", help='path to tree json file')
    parser.add_argument('-n', '--node-file', default="", help='path to node object json file')
    parser.add_argument('-r', '--root-dir', default="", help='path to definitions dir for root')
    parser.add_argument('-e', '--ext-dir', default="", help='path to definitions dir for ext')

    args = parser.parse_args()

    if args.tree_file == "":
        logging.error("\"--tree-file\" is required")
        sys.exit(1)

    if args.node_file == "" and (args.root_dir == "" or args.ext_dir == ""):
        logging.error("\"--root-dir\" and \"--ext-dir\" are required when \"--node-file\" is empty")
        sys.exit(1)

    trees = load_tree_json(args.tree_file)
    objects = load_node_objects(args.node_file, args.root_dir, args.ext_dir)

    for tree in trees:
        t_obj, content = convert(tree, objects)
        # print(json.dumps(t_obj, indent=2))
        # break
        print(json.dumps(t_obj), flush=True)

if __name__ == "__main__":
    main()