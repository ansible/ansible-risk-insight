#!/usr/bin/python
# Copyright 2016 Jakub Jursa <jakub.jursa1@gmail.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: host_aggregate
short_description: Manage OpenStack host aggregates
author: OpenStack Ansible SIG
description:
    - Create, update, or delete OpenStack host aggregates. If a aggregate
      with the supplied name already exists, it will be updated with the
      new name, new availability zone, new metadata and new list of hosts.
options:
  name:
    description: Name of the aggregate.
    required: true
    type: str
  metadata:
    description: Metadata dict.
    type: dict
  availability_zone:
    description: Availability zone to create aggregate into.
    type: str
  hosts:
    description: List of hosts to set for an aggregate.
    type: list
    elements: str
  purge_hosts:
    description: Whether hosts not in I(hosts) should be removed from the aggregate
    type: bool
    default: true
  state:
    description: Should the resource be present or absent.
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
# Create a host aggregate
- openstack.cloud.host_aggregate:
    cloud: mycloud
    state: present
    name: db_aggregate
    hosts:
      - host1
      - host2
    metadata:
      type: dbcluster

# Add an additional host to the aggregate
- openstack.cloud.host_aggregate:
    cloud: mycloud
    state: present
    name: db_aggregate
    hosts:
      - host3
    purge_hosts: false
    metadata:
      type: dbcluster

# Delete an aggregate
- openstack.cloud.host_aggregate:
    cloud: mycloud
    state: absent
    name: db_aggregate
'''

RETURN = '''

'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import OpenStackModule


class ComputeHostAggregateModule(OpenStackModule):
    argument_spec = dict(
        name=dict(required=True),
        metadata=dict(required=False, default=None, type='dict'),
        availability_zone=dict(required=False, default=None),
        hosts=dict(required=False, default=None, type='list', elements='str'),
        purge_hosts=dict(default=True, type='bool'),
        state=dict(default='present', choices=['absent', 'present']),
    )

    module_kwargs = dict(
        supports_check_mode=True
    )

    def _needs_update(self, aggregate):
        new_metadata = (self.params['metadata'] or {})

        if self.params['availability_zone'] is not None:
            new_metadata['availability_zone'] = self.params['availability_zone']

        if self.params['name'] != aggregate.name:
            return True
        if self.params['hosts'] is not None:
            if self.params['purge_hosts']:
                if set(self.params['hosts']) != set(aggregate.hosts):
                    return True
            else:
                intersection = set(self.params['hosts']).intersection(set(aggregate.hosts))
                if set(self.params['hosts']) != intersection:
                    return True
        if self.params['availability_zone'] is not None:
            if self.params['availability_zone'] != aggregate.availability_zone:
                return True
        if self.params['metadata'] is not None:
            if new_metadata != aggregate.metadata:
                return True

        return False

    def _system_state_change(self, aggregate):
        state = self.params['state']
        if state == 'absent' and aggregate:
            return True

        if state == 'present':
            if aggregate is None:
                return True
            return self._needs_update(aggregate)

        return False

    def _update_hosts(self, aggregate, hosts, purge_hosts):
        if hosts is None:
            return

        hosts_to_add = set(hosts) - set(aggregate.get("hosts") or [])
        for i in hosts_to_add:
            self.conn.add_host_to_aggregate(aggregate.id, i)

        if not purge_hosts:
            return

        hosts_to_remove = set(aggregate.get("hosts") or []) - set(hosts)
        for i in hosts_to_remove:
            self.conn.remove_host_from_aggregate(aggregate.id, i)

    def run(self):
        name = self.params['name']
        metadata = self.params['metadata']
        availability_zone = self.params['availability_zone']
        hosts = self.params['hosts']
        purge_hosts = self.params['purge_hosts']
        state = self.params['state']

        if metadata is not None:
            metadata.pop('availability_zone', None)

        aggregates = self.conn.search_aggregates(name_or_id=name)

        if len(aggregates) == 1:
            aggregate = aggregates[0]
        elif len(aggregates) == 0:
            aggregate = None
        else:
            raise Exception("Should not happen")

        if self.ansible.check_mode:
            self.exit_json(changed=self._system_state_change(aggregate))

        if state == 'present':
            if aggregate is None:
                aggregate = self.conn.create_aggregate(
                    name=name, availability_zone=availability_zone)
                self._update_hosts(aggregate, hosts, False)
                if metadata:
                    self.conn.set_aggregate_metadata(aggregate.id, metadata)
                changed = True
            else:
                if self._needs_update(aggregate):
                    if availability_zone is not None:
                        aggregate = self.conn.update_aggregate(
                            aggregate.id, name=name,
                            availability_zone=availability_zone)
                    if metadata is not None:
                        metas = metadata
                        for i in (set(aggregate.metadata.keys()) - set(metadata.keys())):
                            if i != 'availability_zone':
                                metas[i] = None
                        self.conn.set_aggregate_metadata(aggregate.id, metas)
                    self._update_hosts(aggregate, hosts, purge_hosts)
                    changed = True
                else:
                    changed = False
            self.exit_json(changed=changed)

        elif state == 'absent':
            if aggregate is None:
                changed = False
            else:
                self._update_hosts(aggregate, [], True)
                self.conn.delete_aggregate(aggregate.id)
                changed = True
            self.exit_json(changed=changed)


def main():
    module = ComputeHostAggregateModule()
    module()


if __name__ == '__main__':
    main()
