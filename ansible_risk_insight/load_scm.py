import yaml
import json
import argparse
import os
import glob

import task_loader
import module_loader
import role_loader

# library/                  # if any custom modules, put them here (optional)
# module_utils/             # if any custom module_utils to support modules, put them here (optional)
# filter_plugins/           # if any custom filter plugins, put them here (optional)
# site.yml                  # main playbook
# webservers.yml            # playbook for webserver tier
# dbservers.yml             # playbook for dbserver tier
# tasks/                    # task files included from playbooks
#     webservers-extra.yml  # <-- avoids confusing playbook with task files

# roles/
#     common/               # this hierarchy represents a "role"
#         tasks/            #
#             main.yml      #  <-- tasks file can include smaller files if warranted
#         handlers/         #
#             main.yml      #  <-- handlers file
#         templates/        #  <-- files for use with the template resource
#             ntp.conf.j2   #  <------- templates end in .j2
#         files/            #
#             bar.txt       #  <-- files for use with the copy resource
#             foo.sh        #  <-- script files for use with the script resource
#         vars/             #
#             main.yml      #  <-- variables associated with this role
#         defaults/         #
#             main.yml      #  <-- default lower priority variables for this role
#         meta/             #
#             main.yml      #  <-- role dependencies
#         library/          # roles can also include custom modules
#         module_utils/     # roles can also include custom module_utils
#         lookup_plugins/   # or other types of plugins, like lookup in this case

class SCM(object):
    def __init__(self, scm_repo_dir, loaded_role_repos, loaded_collection_repos):
        f = open('task_keywords.txt', 'r')
        self.task_keywords = f.read().splitlines()
        f.close()
        f = open('builtin-modules.txt', 'r')
        self.builtin_modules = f.read().splitlines()
        f.close()
        self.repo = scm_repo_dir

    def defined_modules(self):
        # library/ 
        return 

    def get_playbooks(self):
        
        return 

    def get_roles(self):
        dir = os.path.join(self.repo, "roles")
        rloader = role_loader.RoleLoader()
        roles = rloader.load_role(dir)
        return roles

    def get_tasks(self):
        dir = os.path.join(self.repo, "tasks")
        tloader = task_loader.TaskLoader()
        tasks = tloader.load_task(dir)
        return tasks

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        prog='load_scm.py',
        description=' Analyzer',
        epilog='end',
        add_help=True,
    )

    parser.add_argument('--playbook', help='playbook file')
    parser.add_argument('--project', help='project directory')
    parser.add_argument('--outdir', help='output directory')
    parser.add_argument('--requirements', help='requirements file')
    parser.add_argument('--role_requirements', help='role requirements file')

