#!/usr/bin/python
# coding: utf-8 -*-

# (c) 2015, Hewlett-Packard Development Company, L.P.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: baremetal_node_action
short_description: Activate/Deactivate Bare Metal Resources from OpenStack
author: OpenStack Ansible SIG
description:
    - Deploy to nodes controlled by Ironic.
options:
    name:
      description:
        - Name of the node to create.
      type: str
    state:
      description:
        - Indicates desired state of the resource.
        - I(state) can be C('present'), C('absent'), C('maintenance') or C('off').
      default: present
      type: str
    deploy:
      description:
       - Indicates if the resource should be deployed. Allows for deployment
         logic to be disengaged and control of the node power or maintenance
         state to be changed.
      type: str
      default: 'yes'
    uuid:
      description:
        - globally unique identifier (UUID) to be given to the resource.
      type: str
    ironic_url:
      description:
        - If noauth mode is utilized, this is required to be set to the
          endpoint URL for the Ironic API.  Use with "auth" and "auth_type"
          settings set to None.
      type: str
    config_drive:
      description:
        - A configdrive file or HTTP(S) URL that will be passed along to the
          node.
      type: raw
    instance_info:
      description:
        - Definition of the instance information which is used to deploy
          the node.  This information is only required when an instance is
          set to present.
      type: dict
      suboptions:
        image_source:
          description:
            - An HTTP(S) URL where the image can be retrieved from.
        image_checksum:
          description:
            - The checksum of image_source.
        image_disk_format:
          description:
            - The type of image that has been requested to be deployed.
    power:
      description:
        - A setting to allow power state to be asserted allowing nodes
          that are not yet deployed to be powered on, and nodes that
          are deployed to be powered off.
        - I(power) can be C('present'), C('absent'), C('maintenance') or C('off').
      default: present
      type: str
    maintenance:
      description:
        - A setting to allow the direct control if a node is in
          maintenance mode.
        - I(maintenance) can be C('yes'), C('no'), C('True'), or C('False').
      type: str
    maintenance_reason:
      description:
        - A string expression regarding the reason a node is in a
          maintenance mode.
      type: str
    wait:
      description:
        - A boolean value instructing the module to wait for node
          activation or deactivation to complete before returning.
      type: bool
      default: 'no'
    timeout:
      description:
        - An integer value representing the number of seconds to
          wait for the node activation or deactivation to complete.
      default: 1800
      type: int
requirements:
    - "python >= 3.6"
    - "openstacksdk"

extends_documentation_fragment:
- openstack.cloud.openstack
'''

EXAMPLES = '''
# Activate a node by booting an image with a configdrive attached
- openstack.cloud.baremetal_node_action:
    cloud: "openstack"
    uuid: "d44666e1-35b3-4f6b-acb0-88ab7052da69"
    state: present
    power: present
    deploy: True
    maintenance: False
    config_drive: "http://192.168.1.1/host-configdrive.iso"
    instance_info:
      image_source: "http://192.168.1.1/deploy_image.img"
      image_checksum: "356a6b55ecc511a20c33c946c4e678af"
      image_disk_format: "qcow"
    delegate_to: localhost

# Activate a node by booting an image with a configdrive json object
- openstack.cloud.baremetal_node_action:
    uuid: "d44666e1-35b3-4f6b-acb0-88ab7052da69"
    auth_type: None
    ironic_url: "http://192.168.1.1:6385/"
    config_drive:
      meta_data:
        hostname: node1
        public_keys:
          default: ssh-rsa AAA...BBB==
    instance_info:
      image_source: "http://192.168.1.1/deploy_image.img"
      image_checksum: "356a6b55ecc511a20c33c946c4e678af"
      image_disk_format: "qcow"
    delegate_to: localhost
'''


from ansible_collections.openstack.cloud.plugins.module_utils.ironic import (
    IronicModule,
    ironic_argument_spec,
)
from ansible_collections.openstack.cloud.plugins.module_utils.openstack import (
    openstack_module_kwargs,
    openstack_cloud_from_module
)


def _choose_id_value(module):
    if module.params['uuid']:
        return module.params['uuid']
    if module.params['name']:
        return module.params['name']
    return None


def _is_true(value):
    true_values = [True, 'yes', 'Yes', 'True', 'true', 'present', 'on']
    if value in true_values:
        return True
    return False


def _is_false(value):
    false_values = [False, None, 'no', 'No', 'False', 'false', 'absent', 'off']
    if value in false_values:
        return True
    return False


def _check_set_maintenance(module, cloud, node):
    if _is_true(module.params['maintenance']):
        if _is_false(node['maintenance']):
            cloud.set_machine_maintenance_state(
                node['uuid'],
                True,
                reason=module.params['maintenance_reason'])
            module.exit_json(changed=True, msg="Node has been set into "
                                               "maintenance mode")
        else:
            # User has requested maintenance state, node is already in the
            # desired state, checking to see if the reason has changed.
            if (str(node['maintenance_reason']) not in
                    str(module.params['maintenance_reason'])):
                cloud.set_machine_maintenance_state(
                    node['uuid'],
                    True,
                    reason=module.params['maintenance_reason'])
                module.exit_json(changed=True, msg="Node maintenance reason "
                                                   "updated, cannot take any "
                                                   "additional action.")
    elif _is_false(module.params['maintenance']):
        if node['maintenance'] is True:
            cloud.remove_machine_from_maintenance(node['uuid'])
            return True
    else:
        module.fail_json(msg="maintenance parameter was set but a valid "
                             "the value was not recognized.")
    return False


def _check_set_power_state(module, cloud, node):
    if 'power on' in str(node['power_state']):
        if _is_false(module.params['power']):
            # User has requested the node be powered off.
            cloud.set_machine_power_off(node['uuid'])
            module.exit_json(changed=True, msg="Power requested off")
    if 'power off' in str(node['power_state']):
        if (
            _is_false(module.params['power'])
            and _is_false(module.params['state'])
        ):
            return False
        if (
            _is_false(module.params['power'])
            and _is_false(module.params['state'])
        ):
            module.exit_json(
                changed=False,
                msg="Power for node is %s, node must be reactivated "
                    "OR set to state absent"
            )
        # In the event the power has been toggled on and
        # deployment has been requested, we need to skip this
        # step.
        if (
            _is_true(module.params['power'])
            and _is_false(module.params['deploy'])
        ):
            # Node is powered down when it is not awaiting to be provisioned
            cloud.set_machine_power_on(node['uuid'])
            return True
    # Default False if no action has been taken.
    return False


def main():
    argument_spec = ironic_argument_spec(
        uuid=dict(required=False),
        name=dict(required=False),
        instance_info=dict(type='dict', required=False),
        config_drive=dict(type='raw', required=False),
        state=dict(required=False, default='present'),
        maintenance=dict(required=False),
        maintenance_reason=dict(required=False),
        power=dict(required=False, default='present'),
        deploy=dict(required=False, default='yes'),
        wait=dict(type='bool', required=False, default=False),
        timeout=dict(required=False, type='int', default=1800),
    )
    module_kwargs = openstack_module_kwargs()
    module = IronicModule(argument_spec, **module_kwargs)

    if (
        module.params['config_drive']
        and not isinstance(module.params['config_drive'], (str, dict))
    ):
        config_drive_type = type(module.params['config_drive'])
        msg = ('argument config_drive is of type %s and we expected'
               ' str or dict') % config_drive_type
        module.fail_json(msg=msg)

    node_id = _choose_id_value(module)

    if not node_id:
        module.fail_json(msg="A uuid or name value must be defined "
                             "to use this module.")
    sdk, cloud = openstack_cloud_from_module(module)
    try:
        node = cloud.get_machine(node_id)

        if node is None:
            module.fail_json(msg="node not found")

        uuid = node['uuid']
        instance_info = module.params['instance_info']
        changed = False
        wait = module.params['wait']
        timeout = module.params['timeout']

        # User has requested desired state to be in maintenance state.
        if module.params['state'] == 'maintenance':
            module.params['maintenance'] = True

        if node['provision_state'] in [
                'cleaning',
                'deleting',
                'wait call-back']:
            module.fail_json(msg="Node is in %s state, cannot act upon the "
                                 "request as the node is in a transition "
                                 "state" % node['provision_state'])
        # TODO(TheJulia) This is in-development code, that requires
        # code in the shade library that is still in development.
        if _check_set_maintenance(module, cloud, node):
            if node['provision_state'] in 'active':
                module.exit_json(changed=True,
                                 result="Maintenance state changed")
            changed = True
            node = cloud.get_machine(node_id)

        if _check_set_power_state(module, cloud, node):
            changed = True
            node = cloud.get_machine(node_id)

        if _is_true(module.params['state']):
            if _is_false(module.params['deploy']):
                module.exit_json(
                    changed=changed,
                    result="User request has explicitly disabled "
                           "deployment logic"
                )

            if 'active' in node['provision_state']:
                module.exit_json(
                    changed=changed,
                    result="Node already in an active state."
                )

            if instance_info is None:
                module.fail_json(
                    changed=changed,
                    msg="When setting an instance to present, "
                        "instance_info is a required variable.")

            # TODO(TheJulia): Update instance info, however info is
            # deployment specific. Perhaps consider adding rebuild
            # support, although there is a known desire to remove
            # rebuild support from Ironic at some point in the future.
            cloud.update_machine(uuid, instance_info=instance_info)
            cloud.validate_node(uuid)
            if not wait:
                cloud.activate_node(uuid, module.params['config_drive'])
            else:
                cloud.activate_node(
                    uuid,
                    configdrive=module.params['config_drive'],
                    wait=wait,
                    timeout=timeout)
            # TODO(TheJulia): Add more error checking..
            module.exit_json(changed=changed, result="node activated")

        elif _is_false(module.params['state']):
            if node['provision_state'] not in "deleted":
                cloud.update_machine(uuid, instance_info={})
                if not wait:
                    cloud.deactivate_node(uuid)
                else:
                    cloud.deactivate_node(
                        uuid,
                        wait=wait,
                        timeout=timeout)

                module.exit_json(changed=True, result="deleted")
            else:
                module.exit_json(changed=False, result="node not found")
        else:
            module.fail_json(msg="State must be present, absent, "
                                 "maintenance, off")

    except sdk.exceptions.OpenStackCloudException as e:
        module.fail_json(msg=str(e))


if __name__ == "__main__":
    main()
