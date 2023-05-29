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
import copy
import ansible_risk_insight.logger as logger
from .models import (
    Collection,
    Load,
    LoadType,
    Module,
    Play,
    Playbook,
    Repository,
    Role,
    Task,
    TaskFile,
    PlaybookFormatError,
    TaskFormatError,
)
from .model_loader import (
    load_collection,
    load_module,
    load_playbook,
    load_repository,
    load_role,
    load_taskfile,
)
from .utils import (
    split_target_playbook_fullpath,
    split_target_taskfile_fullpath,
    get_module_specs_by_ansible_doc,
)


class Parser:
    def __init__(self, do_save=False, use_ansible_doc=True, skip_playbook_format_error=True, skip_task_format_error=True):
        self.do_save = do_save
        self.use_ansible_doc = use_ansible_doc
        self.skip_playbook_format_error = skip_playbook_format_error
        self.skip_task_format_error = skip_task_format_error

    def run(self, load_data=None, load_json_path="", collection_name_of_project=""):
        ld = Load()
        if load_data is not None:
            ld = load_data
        elif load_json_path != "":
            if not os.path.exists(load_json_path):
                raise ValueError("file not found: {}".format(load_json_path))
            ld = Load.from_json(open(load_json_path, "r").read())

        collection_name = ""
        role_name = ""
        obj = None
        if ld.target_type == LoadType.COLLECTION:
            collection_name = ld.target_name
            try:
                obj = load_collection(
                    collection_dir=ld.path,
                    basedir=ld.path,
                    use_ansible_doc=self.use_ansible_doc,
                    skip_playbook_format_error=self.skip_playbook_format_error,
                    skip_task_format_error=self.skip_task_format_error,
                    include_test_contents=ld.include_test_contents,
                    load_children=False,
                )
            except PlaybookFormatError:
                if not self.skip_playbook_format_error:
                    raise
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception:
                logger.exception("failed to load the collection {}".format(collection_name))
                return
        elif ld.target_type == LoadType.ROLE:
            role_name = ld.target_name
            try:
                obj = load_role(
                    path=ld.path,
                    basedir=ld.path,
                    use_ansible_doc=self.use_ansible_doc,
                    skip_playbook_format_error=self.skip_playbook_format_error,
                    skip_task_format_error=self.skip_task_format_error,
                    include_test_contents=ld.include_test_contents,
                    load_children=False,
                )
            except PlaybookFormatError:
                if not self.skip_playbook_format_error:
                    raise
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception:
                logger.exception("failed to load the role {}".format(role_name))
                return
        elif ld.target_type == LoadType.PROJECT:
            repo_name = ld.target_name
            try:
                obj = load_repository(
                    path=ld.path,
                    basedir=ld.path,
                    use_ansible_doc=self.use_ansible_doc,
                    skip_playbook_format_error=self.skip_playbook_format_error,
                    skip_task_format_error=self.skip_task_format_error,
                    include_test_contents=ld.include_test_contents,
                )
            except PlaybookFormatError:
                if not self.skip_playbook_format_error:
                    raise
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception:
                logger.exception("failed to load the project {}".format(repo_name))
                return
            if obj.my_collection_name:
                collection_name = obj.my_collection_name
            if collection_name == "" and collection_name_of_project != "":
                collection_name = collection_name_of_project
        elif ld.target_type == LoadType.PLAYBOOK:
            basedir = ""
            target_playbook_path = ""
            if ld.playbook_yaml:
                target_playbook_path = ld.path
            else:
                basedir, target_playbook_path = split_target_playbook_fullpath(ld.path)
            playbook_name = ld.target_name
            try:
                if ld.playbook_only:
                    obj = load_playbook(
                        path=target_playbook_path,
                        yaml_str=ld.playbook_yaml,
                        basedir=basedir,
                        skip_playbook_format_error=self.skip_playbook_format_error,
                        skip_task_format_error=self.skip_task_format_error,
                    )
                else:
                    obj = load_repository(
                        path=basedir,
                        basedir=basedir,
                        target_playbook_path=target_playbook_path,
                        use_ansible_doc=self.use_ansible_doc,
                        skip_playbook_format_error=self.skip_playbook_format_error,
                        skip_task_format_error=self.skip_task_format_error,
                        include_test_contents=ld.include_test_contents,
                    )
            except PlaybookFormatError:
                if not self.skip_playbook_format_error:
                    raise
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception:
                logger.exception("failed to load the playbook {}".format(playbook_name))
                return
        elif ld.target_type == LoadType.TASKFILE:
            basedir = ""
            target_taskfile_path = ""
            if ld.taskfile_yaml:
                target_playbook_path = ld.path
            else:
                basedir, target_taskfile_path = split_target_taskfile_fullpath(ld.path)
            taskfile_name = ld.target_name
            try:
                if ld.taskfile_only:
                    obj = load_taskfile(
                        path=target_taskfile_path,
                        yaml_str=ld.taskfile_yaml,
                        basedir=basedir,
                        skip_task_format_error=self.skip_task_format_error,
                    )
                else:
                    obj = load_repository(
                        path=basedir,
                        basedir=basedir,
                        target_taskfile_path=target_taskfile_path,
                        use_ansible_doc=self.use_ansible_doc,
                        skip_playbook_format_error=self.skip_playbook_format_error,
                        skip_task_format_error=self.skip_task_format_error,
                        include_test_contents=ld.include_test_contents,
                    )
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception:
                logger.exception("failed to load the taskfile {}".format(taskfile_name))
                return
        else:
            raise ValueError("unsupported type: {}".format(ld.target_type))

        mappings = {
            "roles": [],
            "taskfiles": [],
            "modules": [],
            "playbooks": [],
        }

        basedir = ld.path
        if ld.target_type == LoadType.PLAYBOOK:
            basedir, _ = split_target_playbook_fullpath(ld.path)
        elif ld.target_type == LoadType.TASKFILE:
            basedir, _ = split_target_taskfile_fullpath(ld.path)

        roles = []
        for role_path in ld.roles:
            try:
                r = load_role(
                    path=role_path,
                    collection_name=collection_name,
                    basedir=basedir,
                    use_ansible_doc=self.use_ansible_doc,
                    skip_playbook_format_error=self.skip_playbook_format_error,
                    skip_task_format_error=self.skip_task_format_error,
                    include_test_contents=ld.include_test_contents,
                )
                roles.append(r)
            except PlaybookFormatError:
                if not self.skip_playbook_format_error:
                    raise
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception as e:
                logger.debug(f"failed to load a role: {e}")
                continue
            mappings["roles"].append([role_path, r.key])

        taskfiles = [tf for r in roles for tf in r.taskfiles if r.fqcn != ld.target_name]
        for taskfile_path in ld.taskfiles:
            try:
                tf = load_taskfile(
                    path=taskfile_path,
                    yaml_str=ld.taskfile_yaml,
                    role_name=role_name,
                    collection_name=collection_name,
                    basedir=basedir,
                    skip_task_format_error=self.skip_task_format_error,
                )
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception as e:
                logger.debug(f"failed to load a taskfile: {e}")
                continue
            taskfiles.append(tf)
            mappings["taskfiles"].append([taskfile_path, tf.key])

        playbooks = [p for r in roles for p in r.playbooks]
        for playbook_path in ld.playbooks:
            p = None
            try:
                p = load_playbook(
                    path=playbook_path,
                    yaml_str=ld.playbook_yaml,
                    role_name=role_name,
                    collection_name=collection_name,
                    basedir=basedir,
                    skip_playbook_format_error=self.skip_playbook_format_error,
                    skip_task_format_error=self.skip_task_format_error,
                )
            except PlaybookFormatError:
                if not self.skip_playbook_format_error:
                    raise
            except TaskFormatError:
                if not self.skip_task_format_error:
                    raise
            except Exception as e:
                logger.debug(f"failed to load a playbook: {e}")
                continue
            playbooks.append(p)
            mappings["playbooks"].append([playbook_path, p.key])

        plays = [play for p in playbooks for play in p.plays]

        tasks = [t for tf in taskfiles for t in tf.tasks]
        pre_tasks_in_plays = [t for p in plays for t in p.pre_tasks]
        tasks_in_plays = [t for p in plays for t in p.tasks]
        post_tasks_in_plays = [t for p in plays for t in p.post_tasks]
        tasks.extend(pre_tasks_in_plays)
        tasks.extend(tasks_in_plays)
        tasks.extend(post_tasks_in_plays)

        modules = [m for r in roles for m in r.modules]
        module_specs = {}
        if self.use_ansible_doc:
            module_specs = get_module_specs_by_ansible_doc(
                module_files=[fpath for fpath in ld.modules],
                fqcn_prefix=collection_name,
                search_path=ld.path,
            )

        for module_path in ld.modules:
            m = None
            try:
                m = load_module(
                    module_file_path=module_path,
                    role_name=role_name,
                    collection_name=collection_name,
                    basedir=basedir,
                    use_ansible_doc=self.use_ansible_doc,
                    module_specs=module_specs,
                )
            except Exception as e:
                logger.debug(f"failed to load a module: {e}")
                continue
            modules.append(m)
            mappings["modules"].append([module_path, m.key])

        logger.debug("roles: {}".format(len(roles)))
        logger.debug("taskfiles: {}".format(len(taskfiles)))
        logger.debug("modules: {}".format(len(modules)))
        logger.debug("playbooks: {}".format(len(playbooks)))
        logger.debug("plays: {}".format(len(plays)))
        logger.debug("tasks: {}".format(len(tasks)))

        collections = []
        projects = []
        if ld.target_type == LoadType.COLLECTION:
            collections = [obj]
        elif ld.target_type == LoadType.ROLE:
            pass
        elif ld.target_type == LoadType.PLAYBOOK:
            pass
        elif ld.target_type == LoadType.TASKFILE:
            pass
        elif ld.target_type == LoadType.PROJECT:
            projects = [obj]

        if len(collections) > 0:
            collections = [c.children_to_key() for c in collections]
        if len(projects) > 0:
            projects = [p.children_to_key() for p in projects]
        if len(roles) > 0:
            roles = [r.children_to_key() for r in roles]
        if len(taskfiles) > 0:
            taskfiles = [tf.children_to_key() for tf in taskfiles]
        if len(modules) > 0:
            modules = [m.children_to_key() for m in modules]
        if len(playbooks) > 0:
            playbooks = [p.children_to_key() for p in playbooks]
        if len(plays) > 0:
            plays = [p.children_to_key() for p in plays]
        if len(tasks) > 0:
            tasks = [t.children_to_key() for t in tasks]

        # save mappings
        ld.roles = mappings["roles"]
        ld.taskfiles = mappings["taskfiles"]
        ld.playbooks = mappings["playbooks"]
        ld.modules = mappings["modules"]

        definitions = {
            "collections": collections,
            "projects": projects,
            "roles": roles,
            "taskfiles": taskfiles,
            "modules": modules,
            "playbooks": playbooks,
            "plays": plays,
            "tasks": tasks,
        }

        return definitions, ld

    @classmethod
    def restore_definition_objects(cls, input_dir):

        collections = _load_object_list(Collection, os.path.join(input_dir, "collections.json"))

        # TODO: only repository?
        projects = _load_object_list(Repository, os.path.join(input_dir, "projects.json"))

        roles = _load_object_list(Role, os.path.join(input_dir, "roles.json"))

        taskfiles = _load_object_list(TaskFile, os.path.join(input_dir, "taskfiles.json"))

        modules = _load_object_list(Module, os.path.join(input_dir, "modules.json"))

        playbooks = _load_object_list(Playbook, os.path.join(input_dir, "playbooks.json"))

        plays = _load_object_list(Play, os.path.join(input_dir, "plays.json"))

        tasks = _load_object_list(Task, os.path.join(input_dir, "tasks.json"))

        definitions = {
            "collections": collections,
            "projects": projects,
            "roles": roles,
            "taskfiles": taskfiles,
            "modules": modules,
            "playbooks": playbooks,
            "plays": plays,
            "tasks": tasks,
        }

        ld = Load()
        mapping_path = os.path.join(input_dir, "mappings.json")
        if not os.path.exists(mapping_path):
            raise ValueError("file not found: {}".format(mapping_path))
        ld = Load.from_json(open(mapping_path, "r").read())
        return definitions, ld

    @classmethod
    def dump_definition_objects(cls, output_dir, definitions, ld):

        collections = definitions.get("collections", [])
        if len(collections) > 0:
            _dump_object_list(collections, os.path.join(output_dir, "collections.json"))
        projects = definitions.get("projects", [])
        if len(projects) > 0:
            _dump_object_list(projects, os.path.join(output_dir, "projects.json"))

        roles = definitions.get("roles", [])
        if len(roles) > 0:
            _dump_object_list(roles, os.path.join(output_dir, "roles.json"))

        taskfiles = definitions.get("taskfiles", [])
        if len(taskfiles) > 0:
            _dump_object_list(taskfiles, os.path.join(output_dir, "taskfiles.json"))

        modules = definitions.get("modules", [])
        if len(modules) > 0:
            _dump_object_list(modules, os.path.join(output_dir, "modules.json"))

        playbooks = definitions.get("playbooks", [])
        if len(playbooks) > 0:
            _dump_object_list(playbooks, os.path.join(output_dir, "playbooks.json"))

        plays = definitions.get("plays", [])
        if len(plays) > 0:
            _dump_object_list(plays, os.path.join(output_dir, "plays.json"))

        tasks = definitions.get("tasks", [])
        if len(tasks) > 0:
            _dump_object_list(tasks, os.path.join(output_dir, "tasks.json"))

        mapping_path = os.path.join(output_dir, "mappings.json")
        open(mapping_path, "w").write(ld.dump())


def _dump_object_list(obj_list, output_path):
    tmp_obj_list = copy.deepcopy(obj_list)
    lines = []
    for i in range(len(tmp_obj_list)):
        lines.append(tmp_obj_list[i].dump())
    open(output_path, "w").write("\n".join(lines))
    return


def _load_object_list(cls, input_path):
    obj_list = []
    if os.path.exists(input_path):
        with open(input_path, "r") as f:
            for line in f:
                obj = cls.from_json(line)
                obj_list.append(obj)
    return obj_list


def load_name2target_name(path):
    filename = os.path.basename(path)
    parts = os.path.splitext(filename)
    prefix = "load-"
    target_name = parts[0]
    if target_name.startswith(prefix):
        target_name = target_name[len(prefix) :]
    return target_name


# if __name__ == "__main__":
#     parser = argparse.ArgumentParser(
#         prog="parser.py",
#         description=(
#             "parse collection/role and its children and output definition"
#             " json"
#         ),
#         epilog="end",
#         add_help=True,
#     )

#     parser.add_argument(
#         "-l", "--load-path", default="", help="load json path/dir"
#     )
#     parser.add_argument(
#         "-i",
#         "--index-path",
#         default="",
#         help=(
#             "if specified, load files in this index.json (--load-path will be"
#             " ignored)"
#         ),
#     )
#     parser.add_argument(
#         "--root",
#         action="store_true",
#         help="enable this if the target is the root",
#     )
#     parser.add_argument(
#         "--ext",
#         action="store_true",
#         help="enable this if the target is the external dependency(s)",
#     )
#     parser.add_argument(
#         "-o", "--output-dir", default="", help="path to the output dir"
#     )

#     args = parser.parse_args()

#     if not args.root and not args.ext:
#         logger.error('either "--root" or "--ext" must be specified')
#         sys.exit(1)
#     is_ext = args.ext

#     if args.load_path == "" and args.index_path == "":
#         logger.error("either `--load-path` or `--index-path` is required")
#         sys.exit(1)

#     if args.root and args.load_path == "":
#         logger.error('"--load-path" must be specified for "--root" mode')
#         sys.exit(1)

#     if args.root and not os.path.isfile(args.load_path):
#         logger.error(
#             '"--load-path" must be a single .json file for "--root" mode'
#         )
#         sys.exit(1)

#     if args.load_path != "" and not os.path.exists(args.load_path):
#         logger.error("No such file or directory: {}".format(args.load_path))
#         sys.exit(1)

#     if args.index_path != "" and not os.path.exists(args.index_path):
#         logger.error("No such file or directory: {}".format(args.index_path))
#         sys.exit(1)

#     load_json_path_list = []
#     if args.index_path != "":
#         if os.path.isfile(args.index_path):
#             with open(args.index_path, "r") as file:
#                 index_data = json.load(file)
#                 load_dir = index_data.get("out_path", "")
#                 load_json_name_list = index_data.get(
#                     "generated_load_files", []
#                 )
#                 load_json_name_list = [
#                     f.get("file", "") if isinstance(f, dict) else f
#                     for f in load_json_name_list
#                 ]
#                 load_json_path_list = [
#                     os.path.join(load_dir, f) for f in load_json_name_list
#                 ]
#         else:
#             files = os.listdir(args.index_path)
#             index_json_path_list = [
#                 os.path.join(args.index_path, fname)
#                 for fname in files
#                 if fname.startswith("index-") and fname.endswith(".json")
#             ]
#             for i in index_json_path_list:
#                 with open(i, "r") as file:
#                     index_data = json.load(file)
#                     load_dir = index_data.get("out_path", "")
#                     load_json_name_list = index_data.get(
#                         "generated_load_files", []
#                     )
#                     load_json_name_list = [
#                         f.get("file", "") if isinstance(f, dict) else f
#                         for f in load_json_name_list
#                     ]
#                     tmp_load_json_list = [
#                         os.path.join(load_dir, f) for f in load_json_name_list
#                     ]
#                     for load_json_path in tmp_load_json_list:
#                         if load_json_path not in load_json_path_list:
#                             load_json_path_list.append(load_json_path)
#     elif args.load_path != "":
#         if os.path.isfile(args.load_path):
#             load_json_path_list = [args.load_path]
#         else:
#             files = os.listdir(args.load_path)
#             load_json_path_list = [
#                 os.path.join(args.load_path, fname)
#                 for fname in files
#                 if fname.startswith("load-") and fname.endswith(".json")
#             ]

#     if len(load_json_path_list) == 0:
#         logger.info("no load json files found. exitting.")
#         sys.exit()

#     profiles = [
#         (
#             load_json_path,
#             os.path.join(
#                 args.output_dir, load_name2target_name(load_json_path)
#             )
#             if is_ext
#             else args.output_dir,
#         )
#         for load_json_path in load_json_path_list
#     ]

#     num = len(profiles)
#     if num == 0:
#         logger.info("no load json files found. exitting.")
#         sys.exit()
#     else:
#         logger.info("start parsing {} target(s)".format(num))
#     p = Parser()

#     def parse_single(single_input):
#         i = single_input[0]
#         num = single_input[1]
#         load_json_path = single_input[2]
#         output_dir = single_input[3]
#         print("[{}/{}] {}       ".format(i + 1, num, load_json_path))

#         definitions, ld = p.run(load_json_path=load_json_path)

#         if output_dir == "":
#             raise ValueError("Invalid output_dir")
#         if os.path.exists(output_dir):
#             os.makedirs(output_dir, exist_ok=True)
#         Parser.dump_definition_objects(output_dir, definitions, ld)


#     parallel_input_list = [
#         (i, num, load_json_path, output_dir)
#         for i, (load_json_path, output_dir) in enumerate(profiles)
#     ]
#     _ = joblib.Parallel(n_jobs=-1)(
#         joblib.delayed(parse_single)(single_input)
#         for single_input in parallel_input_list
#     )
