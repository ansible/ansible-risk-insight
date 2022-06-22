#!/usr/bin/python

# Copyright (c) 2018 Catalyst IT Ltd.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: coe_cluster
short_description: Add/Remove COE cluster from OpenStack Cloud
author: OpenStack Ansible SIG
description:
   - Add or Remove COE cluster from the OpenStack Container Infra service.
options:
   cluster_template_id:
      description:
         - The template ID of cluster template.
      required: true
      type: str
   discovery_url:
      description:
         - Url used for cluster node discovery
      type: str
   docker_volume_size:
      description:
         - The size in GB of the docker volume
      type: int
   flavor_id:
      description:
         - The flavor of the minion node for this ClusterTemplate
      type: str
   keypair:
      description:
         - Name of the keypair to use.
      type: str
   labels:
      description:
         - One or more key/value pairs
      type: raw
   master_flavor_id:
      description:
         - The flavor of the master node for this ClusterTemplate
      type: str
   master_count:
      description:
         - The number of master nodes for this cluster
      default: 1
      type: int
   name:
      description:
         - Name that has to be given to the cluster template
      required: true
      type: str
   node_count:
      description:
         - The number of nodes for this cluster
      default: 1
      type: int
   state:
      description:
         - Indicate desired state of the resource.
      choices: [present, absent]
      default: present
      type: str
   timeout:
      description:
         - Timeout for creating the cluster in minutes. Default to 60 mins
           if not set
      default: 60
      type: int
requirements:
    - "python >= 3.6"
    - "openstacksdk"

extends_documentation_fragment:
- openstack.cloud.openstack
'''

RETURN = '''
id:
    description: The cluster UUID.
    returned: On success when I(state) is 'present'
    type: str
    sample: "39007a7e-ee4f-4d13-8283-b4da2e037c69"
cluster:
    description: Dictionary describing the cluster.
    returned: On success when I(state) is 'present'
    type: complex
    contains:
      api_address:
          description:
            - Api address of cluster master node
          type: str
          sample: https://172.24.4.30:6443
      cluster_template_id:
          description: The cluster_template UUID
          type: str
          sample: '7b1418c8-cea8-48fc-995d-52b66af9a9aa'
      coe_version:
          description:
            - Version of the COE software currently running in this cluster
          type: str
          sample: v1.11.1
      container_version:
          description:
            - "Version of the container software. Example: docker version."
          type: str
          sample: 1.12.6
      created_at:
          description:
            - The time in UTC at which the cluster is created
          type: str
          sample: "2018-08-16T10:29:45+00:00"
      create_timeout:
          description:
            - Timeout for creating the cluster in minutes. Default to 60 if
              not set.
          type: int
          sample: 60
      discovery_url:
          description:
            - Url used for cluster node discovery
          type: str
          sample: https://discovery.etcd.io/a42ee38e7113f31f4d6324f24367aae5
      faults:
          description:
            - Fault info collected from the Heat resources of this cluster
          type: dict
          sample: {'0': 'ResourceInError: resources[0].resources...'}
      flavor_id:
          description:
            - The flavor of the minion node for this cluster
          type: str
          sample: c1.c1r1
      keypair:
          description:
            - Name of the keypair to use.
          type: str
          sample: mykey
      labels:
          description: One or more key/value pairs
          type: dict
          sample: {'key1': 'value1', 'key2': 'value2'}
      master_addresses:
          description:
            - IP addresses of cluster master nodes
          type: list
          sample: ['172.24.4.5']
      master_count:
          description:
            - The number of master nodes for this cluster.
          type: int
          sample: 1
      master_flavor_id:
          description:
            - The flavor of the master node for this cluster
          type: str
          sample: c1.c1r1
      name:
          description:
            - Name that has to be given to the cluster
          type: str
          sample: k8scluster
      node_addresses:
          description:
            - IP addresses of cluster slave nodes
          type: list
          sample: ['172.24.4.8']
      node_count:
          description:
            - The number of master nodes for this cluster.
          type: int
          sample: 1
      stack_id:
          description:
            - Stack id of the Heat stack
          type: str
          sample: '07767ec6-85f5-44cb-bd63-242a8e7f0d9d'
      status:
          description: Status of the cluster from the heat stack
          type: str
          sample: 'CREATE_COMLETE'
      status_reason:
          description:
            - Status reason of the cluster from the heat stack
          type: str
          sample: 'Stack CREATE completed successfully'
      updated_at:
          description:
            - The time in UTC at which the cluster is updated
          type: str
          sample: '2018-08-16T10:39:25+00:00'
      id:
          description:
            - Unique UUID for this cluster
          type: str
          sample: '86246a4d-a16c-4a58-9e96ad7719fe0f9d'
'''

EXAMPLES = '''
# Create a new Kubernetes cluster
- openstack.cloud.coe_cluster:
    name: k8s
    cluster_template_id: k8s-ha
    keypair: mykey
    master_count: 3
    node_count: 5
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import OpenStackModule


class CoeClusterModule(OpenStackModule):
    argument_spec = dict(
        cluster_template_id=dict(required=True),
        discovery_url=dict(default=None),
        docker_volume_size=dict(type='int'),
        flavor_id=dict(default=None),
        keypair=dict(default=None, no_log=False),
        labels=dict(default=None, type='raw'),
        master_count=dict(type='int', default=1),
        master_flavor_id=dict(default=None),
        name=dict(required=True),
        node_count=dict(type='int', default=1),
        state=dict(default='present', choices=['absent', 'present']),
        timeout=dict(type='int', default=60),
    )
    module_kwargs = dict()

    def _parse_labels(self, labels):
        if isinstance(labels, str):
            labels_dict = {}
            for kv_str in labels.split(","):
                k, v = kv_str.split("=")
                labels_dict[k] = v
            return labels_dict
        if not labels:
            return {}
        return labels

    def run(self):
        params = self.params.copy()

        state = self.params['state']
        name = self.params['name']
        cluster_template_id = self.params['cluster_template_id']

        kwargs = dict(
            discovery_url=self.params['discovery_url'],
            docker_volume_size=self.params['docker_volume_size'],
            flavor_id=self.params['flavor_id'],
            keypair=self.params['keypair'],
            labels=self._parse_labels(params['labels']),
            master_count=self.params['master_count'],
            master_flavor_id=self.params['master_flavor_id'],
            node_count=self.params['node_count'],
            create_timeout=self.params['timeout'],
        )

        changed = False
        cluster = self.conn.get_coe_cluster(
            name_or_id=name, filters={'cluster_template_id': cluster_template_id})

        if state == 'present':
            if not cluster:
                cluster = self.conn.create_coe_cluster(
                    name, cluster_template_id=cluster_template_id, **kwargs)
                changed = True
            else:
                changed = False

            # NOTE (brtknr): At present, create_coe_cluster request returns
            # cluster_id as `uuid` whereas get_coe_cluster request returns the
            # same field as `id`. This behaviour may change in the future
            # therefore try `id` first then `uuid`.
            cluster_id = cluster.get('id', cluster.get('uuid'))
            cluster['id'] = cluster['uuid'] = cluster_id
            self.exit_json(changed=changed, cluster=cluster, id=cluster_id)
        elif state == 'absent':
            if not cluster:
                self.exit_json(changed=False)
            else:
                self.conn.delete_coe_cluster(name)
                self.exit_json(changed=True)


def main():
    module = CoeClusterModule()
    module()


if __name__ == "__main__":
    main()
