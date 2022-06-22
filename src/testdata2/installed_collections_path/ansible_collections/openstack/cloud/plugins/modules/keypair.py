#!/usr/bin/python

# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
# Copyright (c) 2013, Benno Joy <benno@ansible.com>
# Copyright (c) 2013, John Dewey <john@dewey.ws>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: keypair
short_description: Add/Delete a keypair from OpenStack
author: OpenStack Ansible SIG
description:
  - Add or Remove key pair from OpenStack
options:
  name:
    description:
      - Name that has to be given to the key pair
    required: true
    type: str
  public_key:
    description:
      - The public key that would be uploaded to nova and injected into VMs
        upon creation.
    type: str
  public_key_file:
    description:
      - Path to local file containing ssh public key. Mutually exclusive
        with public_key.
    type: str
  state:
    description:
      - Should the resource be present or absent. If state is replace and
        the key exists but has different content, delete it and recreate it
        with the new content.
    choices: [present, absent, replace]
    default: present
    type: str
requirements:
    - "python >= 3.6"
    - "openstacksdk"

extends_documentation_fragment:
- openstack.cloud.openstack
'''

EXAMPLES = '''
# Creates a key pair with the running users public key
- openstack.cloud.keypair:
      cloud: mordred
      state: present
      name: ansible_key
      public_key_file: /home/me/.ssh/id_rsa.pub

# Creates a new key pair and the private key returned after the run.
- openstack.cloud.keypair:
      cloud: rax-dfw
      state: present
      name: ansible_key
'''

RETURN = '''
id:
    description: Unique UUID.
    returned: success
    type: str
name:
    description: Name given to the keypair.
    returned: success
    type: str
public_key:
    description: The public key value for the keypair.
    returned: success
    type: str
private_key:
    description: The private key value for the keypair.
    returned: Only when a keypair is generated for the user (e.g., when creating one
              and a public key is not specified).
    type: str
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import (
    OpenStackModule)


class KeyPairModule(OpenStackModule):
    deprecated_names = ('os_keypair', 'openstack.cloud.os_keypair')

    argument_spec = dict(
        name=dict(required=True),
        public_key=dict(default=None),
        public_key_file=dict(default=None),
        state=dict(default='present',
                   choices=['absent', 'present', 'replace']),
    )

    module_kwargs = dict(
        mutually_exclusive=[['public_key', 'public_key_file']])

    def _system_state_change(self, keypair):
        state = self.params['state']
        if state == 'present' and not keypair:
            return True
        if state == 'absent' and keypair:
            return True
        return False

    def run(self):

        state = self.params['state']
        name = self.params['name']
        public_key = self.params['public_key']

        if self.params['public_key_file']:
            with open(self.params['public_key_file']) as public_key_fh:
                public_key = public_key_fh.read().rstrip()

        keypair = self.conn.get_keypair(name)

        if self.ansible.check_mode:
            self.exit_json(changed=self._system_state_change(keypair))

        if state in ('present', 'replace'):
            if keypair and keypair['name'] == name:
                if public_key and (public_key != keypair['public_key']):
                    if state == 'present':
                        self.fail_json(
                            msg="Key name %s present but key hash not the same"
                                " as offered. Delete key first." % name
                        )
                    else:
                        self.conn.delete_keypair(name)
                        keypair = self.conn.create_keypair(name, public_key)
                        changed = True
                else:
                    changed = False
            else:
                keypair = self.conn.create_keypair(name, public_key)
                changed = True

            self.exit_json(changed=changed, key=keypair, id=keypair['id'])

        elif state == 'absent':
            if keypair:
                self.conn.delete_keypair(name)
                self.exit_json(changed=True)
            self.exit_json(changed=False)


def main():
    module = KeyPairModule()
    module()


if __name__ == '__main__':
    main()
