#!/usr/bin/python

# Copyright (c) 2021 T-Systems International GmbH
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: keypair_info
short_description: Get information about keypairs from OpenStack
author: OpenStack Ansible SIG
description:
  - Get information about keypairs that are associated with the account
options:
  name:
    description:
      - Name or ID of the keypair
    type: str
  user_id:
    description:
      - It allows admin users to operate key-pairs of specified user ID.
    type: str
  limit:
    description:
      - Requests a page size of items.
      - Returns a number of items up to a limit value.
    type: int
  marker:
    description:
      - The last-seen item.
    type: str
requirements:
    - "python >= 3.6"
    - "openstacksdk"

extends_documentation_fragment:
- openstack.cloud.openstack
'''

EXAMPLES = '''
- name: Get information about keypairs
  openstack.cloud.keypair_info:
  register: result

- name: Get information about keypairs using optional parameters
  openstack.cloud.keypair_info:
    name: "test"
    user_id: "fed75b36fd7a4078a769178d2b1bd844"
    limit: 10
    marker: "jdksl"
  register: result
'''

RETURN = '''
openstack_keypairs:
  description:
    - Lists keypairs that are associated with the account.
  type: complex
  returned: always
  contains:
    created_at:
      description:
        - The date and time when the resource was created.
      type: str
      sample: "2021-01-19T14:52:07.261634"
    id:
      description:
        - The id identifying the keypair
      type: str
      sample: "keypair-5d935425-31d5-48a7-a0f1-e76e9813f2c3"
    is_deleted:
      description:
        - A boolean indicates whether this keypair is deleted or not.
      type: bool
    fingerprint:
      description:
        - The fingerprint for the keypair.
      type: str
      sample: "7e:eb:ab:24:ba:d1:e1:88:ae:9a:fb:66:53:df:d3:bd"
    name:
      description:
        - A keypair name which will be used to reference it later.
      type: str
      sample: "keypair-5d935425-31d5-48a7-a0f1-e76e9813f2c3"
    private_key:
      description:
        - The private key for the keypair.
      type: str
      sample: "MIICXAIBAAKBgQCqGKukO ... hZj6+H0qtjTkVxwTCpvKe4eCZ0FPq"
    public_key:
      description:
        - The keypair public key.
      type: str
      sample: "ssh-rsa AAAAB3NzaC1yc ... 8rPsBUHNLQp Generated-by-Nova"
    type:
      description:
        - The type of the keypair.
        - Allowed values are ssh or x509.
      type: str
      sample: "ssh"
    user_id:
      description:
        - It allows admin users to operate key-pairs of specified user ID.
      type: str
      sample: "59b10f2a2138428ea9358e10c7e44444"
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import (
    OpenStackModule)


class KeyPairInfoModule(OpenStackModule):
    argument_spec = dict(
        name=dict(type='str', required=False),
        user_id=dict(type='str', required=False),
        limit=dict(type='int', required=False),
        marker=dict(type='str', required=False)
    )
    module_kwargs = dict(
        supports_check_mode=True
    )

    def run(self):
        name = self.params['name']
        user_id = self.params['user_id']
        limit = self.params['limit']
        marker = self.params['marker']

        filters = {}
        data = []

        if user_id:
            filters['user_id'] = user_id
        if limit:
            filters['limit'] = limit
        if marker:
            filters['marker'] = marker

        result = self.conn.search_keypairs(name_or_id=name,
                                           filters=filters)
        raws = [raw if isinstance(raw, dict) else raw.to_dict()
                for raw in result]

        for raw in raws:
            raw.pop('location')
            data.append(raw)

        self.exit(changed=False, openstack_keypairs=data)


def main():
    module = KeyPairInfoModule()
    module()


if __name__ == '__main__':
    main()
