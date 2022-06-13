import yaml
import os
from ansible.cli.galaxy import GalaxyCLI

import struct
import task_loader
import module_loader
import role_loader

class ExternalDependency(object):
    def __init__(self, requirements, tmp_dir):
        self.tmp_dir = tmp_dir
        self.collections = []
        self.roles = []

    def setup_tmpdir(self, tmp_dir):
        if not os.path.exists(tmp_dir):
            print("creating tmp dir...")
            os.mkdir(tmp_dir)
        return

    def collection_install_requirements(self, requirements, dir):
        # requirements.yml
        # r_file = os.path.join(self._project_dir, 'requirements.yml')
        print("installing ", requirements)
        if os.path.exists(requirements):
            galaxy_args = ['ansible-galaxy', 'collection', 'install', '-r', requirements,
                '-p', dir]
            gcli = GalaxyCLI(args=galaxy_args)
            gcli.run()
        return

    def collection_install(self, collection, dir):
        print("install collection", collection)
        galaxy_args = ['ansible-galaxy', 'collection', 'install', collection,
        '-p', dir]
        gcli = GalaxyCLI(args=galaxy_args)
        gcli.run()
        return

    def install_requirements_role(self, requirements, dir):
        # requirements.yml
        # r_file = os.path.join(self._project_dir, 'requirements.yml')
        print("installing ", requirements)
        if os.path.exists(requirements):
            galaxy_args = ['ansible-galaxy', 'install', '-r', requirements,
                '-p', dir]
            gcli = GalaxyCLI(args=galaxy_args)
            gcli.run()
        return
    
    def load_dependent_role(self, dir):
        rloader = role_loader.RoleLoader()
        role_repos = rloader.load_role(dir)
        return role_repos


    def load_dependent_collection(self, dir):
        collections = []
        # tmp/ansible_collections/
        # collection/
        # ├── plugins/
        # │   ├── modules/
        # ├── roles/
        # ├── playbooks/
        # │   ├── files/
        # │   └── tasks/
        cdir = os.path.join(dir, "ansible_collections")
        files = os.listdir(cdir)
        col_dir = [f for f in files if os.path.isdir(os.path.join(cdir, f))]
        for c in col_dir:
            col = struct.Collection()
            col.name = c
            tloader = task_loader.TaskLoader()
            col.tasks = tloader.get_tasks_from_collection(dir)
            mloader = module_loader.ModuleLoader()
            col.modules = mloader.get_module_from_collection(dir)
            col.playbooks = self.get_playbooks_from_collection(dir)
            collections.append(col)
        return collections



    def get_playbooks_from_collection(self, dir):
        playbooks = []
        # tmp/ansible_collections/collection/playbooks
        # playbook file list
        return playbooks