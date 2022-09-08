#!/usr/bin/python

# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2013, Benno Joy <benno@ansible.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: object
short_description: Create or Delete objects and containers from OpenStack
author: OpenStack Ansible SIG
description:
   - Create or Delete objects and containers from OpenStack
options:
   container:
     description:
        - The name of the container in which to create the object
     required: true
     type: str
   name:
     description:
        - Name to be give to the object. If omitted, operations will be on
          the entire container
     required: false
     type: str
   filename:
     description:
        - Path to local file to be uploaded.
     required: false
     type: str
   container_access:
     description:
        - desired container access level.
     required: false
     choices: ['private', 'public']
     default: private
     type: str
   state:
     description:
       - Should the resource be present or absent.
     choices: [present, absent]
     default: present
     type: str
requirements:
    - "python >= 3.6"
    - "openstacksdk"

extends_documentation_fragment:
- openstack.cloud.openstack
'''

EXAMPLES = '''
- name: "Create a object named 'fstab' in the 'config' container"
  openstack.cloud.object:
    cloud: mordred
    state: present
    name: fstab
    container: config
    filename: /etc/fstab

- name: Delete a container called config and all of its contents
  openstack.cloud.object:
    cloud: rax-iad
    state: absent
    container: config
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import OpenStackModule


class SwiftObjectModule(OpenStackModule):
    argument_spec = dict(
        name=dict(required=False, default=None),
        container=dict(required=True),
        filename=dict(required=False, default=None),
        container_access=dict(default='private', choices=['private', 'public']),
        state=dict(default='present', choices=['absent', 'present']),
    )
    module_kwargs = dict()

    def process_object(
        self, container, name, filename, container_access, **kwargs
    ):
        changed = False
        container_obj = self.conn.get_container(container)
        if kwargs['state'] == 'present':
            if not container_obj:
                container_obj = self.conn.create_container(container)
                changed = True
            if self.conn.get_container_access(container) != container_access:
                self.conn.set_container_access(container, container_access)
                changed = True
            if name:
                if self.conn.is_object_stale(container, name, filename):
                    self.conn.create_object(container, name, filename)
                    changed = True
        else:
            if container_obj:
                if name:
                    if self.conn.get_object_metadata(container, name):
                        self.conn.delete_object(container, name)
                    changed = True
                else:
                    self.conn.delete_container(container)
                    changed = True
        return changed

    def run(self):
        changed = self.process_object(**self.params)

        self.exit_json(changed=changed)


def main():
    module = SwiftObjectModule()
    module()


if __name__ == "__main__":
    main()
