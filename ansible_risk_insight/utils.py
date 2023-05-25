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
import traceback
import subprocess
import requests
import hashlib
import yaml
import json
from filelock import FileLock
from copy import deepcopy
from tabulate import tabulate
from inspect import isclass
from importlib.util import spec_from_file_location, module_from_spec

import ansible_risk_insight.logger as logger


def lock_file(fpath, timeout=10):
    if not fpath:
        return
    lockfile = get_lock_file_name(fpath)
    lock = FileLock(lockfile, timeout=timeout)
    lock.acquire()
    return lock


def unlock_file(lock):
    if not lock:
        return
    if not isinstance(lock, FileLock):
        return
    lock.release()


def remove_lock_file(lock):
    if not lock:
        return
    if not isinstance(lock, FileLock):
        return
    lockfile = lock.lock_file
    if not lockfile:
        return
    if not os.path.exists(lockfile):
        return
    os.remove(lockfile)


def get_lock_file_name(fpath):
    return fpath + ".lock"


def install_galaxy_target(target, target_type, output_dir, source_repository="", target_version=""):
    server_option = ""
    if source_repository:
        server_option = "--server {}".format(source_repository)
    target_name = target
    if target_version:
        target_name = f"{target}:{target_version}"
    logger.debug("exec ansible-galaxy cmd: ansible-galaxy {} install {} {} -p {}".format(target_type, target_name, server_option, output_dir))
    proc = subprocess.run(
        "ansible-galaxy {} install {} {} -p {}".format(target_type, target_name, server_option, output_dir),
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def install_github_target(target, output_dir):
    proc = subprocess.run(
        "git clone {} {}".format(target, output_dir),
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    return proc.stdout


def get_download_metadata(typ: str, install_msg: str):
    download_url = ""
    version = ""
    if typ == "collection":
        for line in install_msg.splitlines():
            if line.startswith("Downloading "):
                download_url = line.split(" ")[1]
                version = download_url.split("-")[-1].replace(".tar.gz", "")
                break
    elif typ == "role":
        for line in install_msg.splitlines():
            if line.startswith("- downloading role from "):
                download_url = line.split(" ")[-1]
                version = download_url.split("/")[-1].replace(".tar.gz", "")
                break
    hash = ""
    if download_url != "":
        hash = get_hash_of_url(download_url)
    return download_url, version, hash


def get_installed_metadata(type, name, path, dep_dir=None):
    if dep_dir:
        dep_dir_alt = os.path.join(dep_dir, "ansible_collections")
        if os.path.exists(dep_dir_alt):
            dep_dir = dep_dir_alt
        parts = name.split(".")
        if len(parts) == 1:
            parts.append("dummy")
        dep_dir_target_path = os.path.join(dep_dir, parts[0], parts[1])
        download_url, version = get_installed_metadata(type, name, dep_dir_target_path)
        if download_url or version:
            return download_url, version
    download_url = ""
    version = ""
    galaxy_yml = "GALAXY.yml"
    galaxy_data = None
    if type == "collection":
        base_dir = "/".join(path.split("/")[:-2])
        dirs = os.listdir(base_dir)
        for dir_name in dirs:
            tmp_galaxy_data = None
            if dir_name.startswith(name) and dir_name.endswith(".info"):
                galaxy_yml_path = os.path.join(base_dir, dir_name, galaxy_yml)
                try:
                    with open(galaxy_yml_path, "r") as galaxy_yml_file:
                        tmp_galaxy_data = yaml.safe_load(galaxy_yml_file)
                except Exception:
                    pass
            if isinstance(tmp_galaxy_data, dict):
                galaxy_data = tmp_galaxy_data
    if galaxy_data is not None:
        download_url = galaxy_data.get("download_url", "")
        version = galaxy_data.get("version", "")
    return download_url, version


def get_collection_metadata(path: str):
    if not os.path.exists(path):
        return None
    manifest_json_path = os.path.join(path, "MANIFEST.json")
    meta = None
    if os.path.exists(manifest_json_path):
        with open(manifest_json_path, "r") as file:
            meta = json.load(file)
    return meta


def get_role_metadata(path: str):
    if not os.path.exists(path):
        return None
    meta_main_yml_path = os.path.join(path, "meta", "main.yml")
    meta = None
    if os.path.exists(meta_main_yml_path):
        with open(meta_main_yml_path, "r") as file:
            meta = yaml.safe_load(file)
    return meta


def escape_url(url: str):
    base_url = url.split("?")[0]
    replaced = base_url.replace("://", "__").replace("/", "_")
    return replaced


def escape_local_path(path: str):
    replaced = path.replace("/", "__")
    return replaced


def get_hash_of_url(url: str):
    response = requests.get(url)
    hash = hashlib.sha256(response.content).hexdigest()
    return hash


def split_name_and_version(target_name):
    name = target_name
    version = ""
    if ":" in target_name:
        parts = target_name.split(":")
        name = parts[0]
        version = parts[1]
    return name, version


def split_target_playbook_fullpath(fullpath: str):
    basedir = os.path.dirname(fullpath)
    if "/playbooks/" in fullpath:
        basedir = fullpath.split("/playbooks/")[0]
    target_playbook_path = fullpath.replace(basedir, "")
    if target_playbook_path[0] == "/":
        target_playbook_path = target_playbook_path[1:]
    return basedir, target_playbook_path


def split_target_taskfile_fullpath(fullpath: str):
    basedir = os.path.dirname(fullpath)
    if "/roles/" in fullpath:
        basedir = fullpath.split("/roles/")[0]
    target_taskfile_path = fullpath.replace(basedir, "")
    if target_taskfile_path[0] == "/":
        target_taskfile_path = target_taskfile_path[1:]
    return basedir, target_taskfile_path


def version_to_num(ver: str):
    if ver == "unknown":
        return 0
    # version string can be 1.2.3-abcdxyz
    ver_num_part = ver.split("-")[0]
    parts = ver_num_part.split(".")
    num = 0
    if len(parts) >= 1:
        if parts[0].isnumeric():
            num += float(parts[0])
    if len(parts) >= 2:
        if parts[1].isnumeric():
            num += float(parts[1]) * (0.001**1)
    if len(parts) >= 3:
        if parts[2].isnumeric():
            num += float(parts[2]) * (0.001**2)
    return num


def is_url(txt: str):
    return "://" in txt


def is_local_path(txt: str):
    if is_url(txt):
        return False
    if "/" in txt:
        return True
    if os.path.exists(txt):
        return True


def indent(multi_line_txt, level=0):
    lines = multi_line_txt.splitlines()
    lines = [" " * level + line for line in lines if line.replace(" ", "") != ""]
    return "\n".join(lines)


def report_to_display(data_report: dict):
    playbook_num_total = data_report["summary"].get("playbooks", {}).get("total", 0)
    # playbook_num_risk_found = data_report["summary"].get("playbooks", {}).get("risk_found", 0)
    role_num_total = data_report["summary"].get("roles", {}).get("total", 0)
    # role_num_risk_found = data_report["summary"].get("roles", {}).get("risk_found", 0)

    output_txt = ""
    output_txt += "-" * 90 + "\n"
    output_txt += "Ansible Risk Insight Report\n"
    output_txt += "-" * 90 + "\n"

    if playbook_num_total + role_num_total == 0:
        output_txt += "No playbooks and roles found\n"
    else:
        found_contents = ""
        if playbook_num_total > 0:
            found_contents += f"{playbook_num_total} playbooks"

        if role_num_total > 0:
            if found_contents != "":
                found_contents += " and "
            found_contents += f"{role_num_total} roles"

        output_txt += f"{found_contents} found\n"

    output_txt += "-" * 90 + "\n"

    report_num = 1
    for detail in data_report["details"]:
        output_txt_for_this_tree = ""
        do_report = False
        # output_txt_for_this_tree += "#{} {} - {}\n".format(report_num, tree_root_type.upper(), tree_root_name)
        results_list = detail.get("results", [])

        for result_info in results_list:
            output = result_info.get("output", "")
            if output == "":
                continue
            do_report = True
            # output_txt_for_this_tree += rule_name + "\n"
            output_txt_for_this_tree += indent(output, 0) + "\n"
        output_txt_for_this_tree += "-" * 90 + "\n"
        if do_report:
            output_txt += output_txt_for_this_tree
            report_num += 1
    return output_txt


def summarize_findings(findings, show_all: bool = False):
    metadata = findings.metadata
    dependencies = findings.dependencies
    report = findings.report
    resolve_failures = findings.resolve_failures
    extra_requirements = findings.extra_requirements
    return summarize_findings_data(metadata, dependencies, report, resolve_failures, extra_requirements, show_all)


def summarize_findings_data(metadata, dependencies, report, resolve_failures, extra_requirements, show_all: bool = False):
    target_name = metadata.get("name", "")
    output_lines = []

    report_txt = report_to_display(report)
    output_lines.append(report_txt)

    if len(dependencies) > 0:
        output_lines.append("External Dependencies")
        dep_table = [("NAME", "VERSION", "HASH")]
        for dep_info in dependencies:
            dep_meta = dep_info.get("metadata", {})
            dep_name = dep_meta.get("name", "")
            if dep_name == target_name:
                continue
            dep_version = dep_meta.get("version", "")
            dep_hash = dep_meta.get("hash", "")
            dep_table.append((dep_name, dep_version, dep_hash))
        output_lines.append(tabulate(dep_table))

    #     print("-" * 90)
    #     print("ARI scan completed!")
    #     print(f"Findings have been saved at: {self.ram_client.make_findings_dir_path(self.type, self.name, self.version, self.hash)}")
    #     print("-" * 90)

    module_failures = resolve_failures.get("module", {})
    role_failures = resolve_failures.get("role", {})
    taskfile_failures = resolve_failures.get("taskfile", {})
    module_fail_num = len(module_failures)
    role_fail_num = len(role_failures)
    taskfile_fail_num = len(taskfile_failures)
    total_fail_num = module_fail_num + role_fail_num + taskfile_fail_num
    if total_fail_num > 0:
        output_lines.append(f"Failed to resolve {module_fail_num} modules, {role_fail_num} roles, {taskfile_fail_num} taskfiles")
    if module_fail_num > 0:
        output_lines.append("- modules: ")
        for module_action in module_failures:
            called_num = module_failures[module_action]
            output_lines.append(f"  - {module_action}    ({called_num} times called)")
    if role_fail_num > 0:
        output_lines.append("- roles: ")
        for role_action in role_failures:
            called_num = role_failures[role_action]
            output_lines.append(f"  - {role_action}    ({called_num} times called)")
    if taskfile_fail_num > 0:
        output_lines.append("- taskfiles: ")
        for taskfile_action in taskfile_failures:
            called_num = taskfile_failures[taskfile_action]
            output_lines.append(f"  - {taskfile_action}    ({called_num} times called)")

    # roles = set()
    if len(extra_requirements) > 0:
        unresolved_modules = []
        unresolved_roles = []
        suggestion = {}
        for ext_req in extra_requirements:
            if ext_req.get("type", "") not in ["role", "module"]:
                continue
            req_name = ext_req.get("defined_in", {}).get("name", None)
            if req_name is None:
                continue
            if req_name == target_name:
                continue
            # print(f"[DEBUG] requirement: {ext_req}")

            obj_type = ext_req.get("type", "")
            obj_name = ext_req.get("name", "")
            short_name = obj_name.replace(f"{req_name}.", "")

            if obj_type == "module":
                unresolved_modules.append(ext_req)
            if obj_type == "role":
                unresolved_roles.append(ext_req)

            req_version = ext_req.get("defined_in", {}).get("version", None)
            req_str = json.dumps([req_name, req_version])

            if req_str not in suggestion:
                suggestion[req_str] = {"module": [], "role": []}
            suggestion[req_str][obj_type].append(short_name)

        if len(unresolved_modules) > 0:
            output_lines.append("Unresolved modules:")
            table = [("NAME", "USED_IN")]
            thresh = 4
            for ext_req in unresolved_modules[:thresh]:
                obj_name = ext_req.get("name", "")
                used_in = ext_req.get("used_in", "")
                req_name = ext_req.get("defined_in", {}).get("name", None)
                short_name = obj_name.replace(f"{req_name}.", "")
                table.append((short_name, used_in))
            if len(unresolved_modules) > thresh:
                rest_num = len(unresolved_modules) - thresh
                table.append(("", f"... and {rest_num} other modules"))
            output_lines.append(tabulate(table))

        if len(unresolved_roles) > 0:
            output_lines.append("Unresolved roles:")
            table = [("NAME", "USED_IN")]
            thresh = 4
            for ext_req in unresolved_roles[:thresh]:
                obj_name = ext_req.get("name", "")
                used_in = ext_req.get("used_in", "")
                req_name = ext_req.get("defined_in", {}).get("name", None)
                short_name = obj_name.replace(f"{req_name}.", "")
                table.append((short_name, used_in))
            if len(unresolved_roles) > thresh:
                rest_num = len(unresolved_roles) - thresh
                table.append(("", f"... and {rest_num} other roles"))
            output_lines.append(tabulate(table))

        req_name_keys = sorted(list(suggestion.keys()))
        output_lines.append("")
        output_lines.append("-- Suggested Dependencies --")
        table_data = [("NAME", "VERSION", "SUGGESTED_FOR")]
        for req_str in req_name_keys:
            req_dict = suggestion[req_str]
            req_module_list = req_dict["module"]
            req_module_num = len(req_module_list)

            req_role_list = req_dict["role"]
            req_role_num = len(req_role_list)
            if req_module_num + req_role_num == 0:
                continue

            req_info = json.loads(req_str)
            req_name = req_info[0]
            req_version = req_info[1]

            summary_str = ""
            thresh = 3
            if req_module_num > 0:
                module_names = ", ".join(req_module_list[:thresh])
                if req_module_num > thresh:
                    module_names += ", etc."
                prefix = "module" if req_module_num == 1 else "modules"
                module_names += f" (total {req_module_num} {prefix})"
                summary_str += module_names
            if req_role_num > 0:
                if summary_str != "":
                    summary_str += " and "

                role_names = ", ".join(req_role_list[:thresh])
                if req_role_num > thresh:
                    role_names += ", etc."
                prefix = "role" if req_role_num == 1 else "roles"
                role_names += f" (total {req_role_num} {prefix})"
                summary_str += role_names
            table_data.append((req_name, req_version, summary_str))
        output_lines.append(tabulate(table_data))
    output = "\n".join(output_lines)
    return output


def show_all_ram_metadata(ram_meta_list):
    table = [("NAME", "VERSION", "HASH")]
    for meta in ram_meta_list:
        table.append((meta["name"], meta["version"], meta["hash"]))
    print(tabulate(table))


def diff_files_data(files1, files2):
    files_dict1 = {}
    for finfo in files1.get("files", []):
        ftype = finfo.get("ftype", "")
        if ftype != "file":
            continue
        fpath = finfo.get("name", "")
        hash = finfo.get("chksum_sha256", "")
        files_dict1[fpath] = hash

    files_dict2 = {}
    for finfo in files2.get("files", []):
        ftype = finfo.get("ftype", "")
        if ftype != "file":
            continue
        fpath = finfo.get("name", "")
        hash = finfo.get("chksum_sha256", "")
        files_dict2[fpath] = hash

    # TODO: support "replaced" type
    diffs = []
    for fpath, hash in files_dict1.items():
        if fpath in files_dict2:
            if files_dict2[fpath] == hash:
                continue
            else:
                diffs.append(
                    {
                        "type": "updated",
                        "filepath": fpath,
                    }
                )
        else:
            diffs.append(
                {
                    "type": "created",
                    "filepath": fpath,
                }
            )

    for fpath, hash in files_dict2.items():
        if fpath in files_dict1:
            continue
        else:
            diffs.append(
                {
                    "type": "deleted",
                    "filepath": fpath,
                }
            )

    return diffs


def show_diffs(diffs):
    table = [("NAME", "DIFF_TYPE")]
    for d in diffs:
        table.append((d["filepath"], d["type"]))
    print(tabulate(table))


def get_module_specs_by_ansible_doc(module_files: str, fqcn_prefix: str, search_path: str):
    if not module_files:
        return {}

    if search_path and fqcn_prefix:
        parent_path_pattern = "/" + fqcn_prefix.replace(".", "/")
        if parent_path_pattern in search_path:
            search_path = search_path.split(parent_path_pattern)[0]

    fqcn_list = []
    for module_file_path in module_files:
        module_name = os.path.basename(module_file_path)
        if module_name[-3:] == ".py":
            module_name = module_name[:-3]
        if module_name == "__init__":
            continue
        fqcn = module_name
        if fqcn_prefix:
            fqcn = fqcn_prefix + "." + module_name
        fqcn_list.append(fqcn)
    if not fqcn_list:
        return {}
    fqcn_list_str = " ".join(fqcn_list)
    cmd_args = [f"ansible-doc {fqcn_list_str} --json"]
    _env = os.environ.copy()
    _env["ANSIBLE_COLLECTIONS_PATH"] = search_path
    proc = subprocess.run(args=cmd_args, shell=True, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=_env)
    if proc.stderr and not proc.stdout:
        logger.debug(f"error while getting the documentation for modules `{fqcn_list_str}`: {proc.stderr}")
        return ""
    wrapper_dict = json.loads(proc.stdout)
    specs = {}
    for fqcn in wrapper_dict:
        doc_dict = wrapper_dict[fqcn].get("doc", {})
        doc = yaml.safe_dump(doc_dict)
        examples = wrapper_dict[fqcn].get("examples", "")
        specs[fqcn] = {
            "doc": doc,
            "examples": examples,
        }
    return specs


def get_documentation_in_module_file(fpath: str):
    if not fpath:
        return ""
    if not os.path.exists(fpath):
        return ""
    lines = []
    with open(fpath, "r") as file:
        for line in file:
            lines.append(line)
    doc_lines = []
    is_inside_doc = False
    quotation = ""
    for line in lines:
        stripped_line = line.strip()

        if is_inside_doc and quotation and stripped_line.startswith(quotation):
            is_inside_doc = False
            break

        if is_inside_doc:
            if quotation:
                doc_lines.append(line)
            else:
                if "'''" in line:
                    quotation = "'''"
                if '"""' in line:
                    quotation = '"""'

        if stripped_line.startswith("DOCUMENTATION"):
            is_inside_doc = True
            if "'''" in line:
                quotation = "'''"
            if '"""' in line:
                quotation = '"""'
    return "\n".join(doc_lines)


def get_class_by_arg_type(arg_type: str):
    if not isinstance(arg_type, str):
        return None

    mapping = {
        "str": str,
        "list": list,
        "dict": dict,
        "bool": bool,
        "int": int,
        "float": float,
        # ARI handles `path` as a string
        "path": str,
        "raw": any,
        # TODO: check actual types of the following
        "jsonarg": str,
        "json": str,
        "bytes": str,
        "bits": str,
    }

    if arg_type not in mapping:
        return None

    return mapping[arg_type]


def load_classes_in_dir(dir_path: str, target_class: type, base_dir: str = "", only_subclass: bool = True, fail_on_error: bool = False):
    search_path = dir_path
    found = False
    if os.path.exists(search_path):
        found = True
    if not found and base_dir:
        self_path = os.path.abspath(base_dir)
        search_path = os.path.join(os.path.dirname(self_path), dir_path)
        if os.path.exists(search_path):
            found = True

    if not found:
        raise ValueError(f'Path not found "{dir_path}"')

    files = os.listdir(search_path)
    scripts = [os.path.join(search_path, f) for f in files if f[-3:] == ".py"]
    classes = []
    errors = []
    for s in scripts:
        try:
            short_module_name = os.path.basename(s)[:-3]
            spec = spec_from_file_location(short_module_name, s)
            mod = module_from_spec(spec)
            spec.loader.exec_module(mod)
            for k in mod.__dict__:
                cls = getattr(mod, k)
                if not callable(cls):
                    continue
                if not isclass(cls):
                    continue
                if not issubclass(cls, target_class):
                    continue
                if only_subclass and cls == target_class:
                    continue
                classes.append(cls)
        except Exception:
            exc = traceback.format_exc()
            msg = f"failed to load a rule module {s}: {exc}"
            if fail_on_error:
                raise ValueError(msg)
            else:
                errors.append(msg)
    return classes, errors


def equal(a: any, b: any):
    type_a = type(a)
    type_b = type(b)
    if type_a != type_b:
        return False
    if type_a == dict:
        all_keys = list(a.keys()) + list(b.keys())
        for key in all_keys:
            val_a = a.get(key, None)
            val_b = b.get(key, None)
            if not equal(val_a, val_b):
                return False
    elif type_a == list:
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            val_a = a[i]
            val_b = b[i]
            if not equal(val_a, val_b):
                return False
    elif hasattr(a, "__dict__"):
        if not equal(a.__dict__, b.__dict__):
            return False
    else:
        if a != b:
            return False
    return True


def recursive_copy_dict(src, dst):
    if not isinstance(src, dict):
        raise ValueError(f"only dict input is allowed, but got {type(src)}")

    if not isinstance(dst, dict):
        raise ValueError(f"only dict input is allowed, but got {type(dst)}")

    for k, sv in src.items():
        if isinstance(sv, dict):
            dst[k] = {}
            recursive_copy_dict(sv, dst[k])
        else:
            dst[k] = deepcopy(sv)
    return


def is_test_object(path: str):
    return path.startswith("tests/integration/") or path.startswith("molecule/")
