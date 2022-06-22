from ansible.module_utils.basic import AnsibleModule

ANSIBLE_METADATA = {'metadata_version': '1.0', 'status': ['preview'],
                    'supported_by': 'community'}

DOCUMENTATION = \
    '''
---
module: odl_usermod
short_description: Manipulate ODL users
description:
    - Use this module to add, delete and list ODL users
version_added: "1.0"
author: "Taseer Ahmed (@Taseer)"
options:
notes:
requirements:
'''

RETURN = \
    '''
message:
  description: Add/remove/list OpenDaylight users
'''

EXAMPLES = \
    '''
---
- hosts: localhost
  tasks:
    - name: create odl user
      odl_usermod:
        username: admin
        password: admin
        state: present

    - name: delete odl user
      odl_usermod:
        username: admin
        state: absent

    - name: list odl users
      odl_usermod:
        state: list

    - name: change user password
      odl_usermod:
        username: admin
        password: admin
        state: update
'''


def build_cmd(module, *args):
    cmd = [
        module.get_bin_path('java', True),
        '-jar',
        '/opt/opendaylight/bin/aaa-cli-jar.jar',
        '--dbd',
        '/opt/opendaylight/data'
        ]
    for arg in args:
        cmd.append(arg)
    return cmd


def main():
    module = AnsibleModule(
        argument_spec=dict(
            username=dict(type='str'),
            password=dict(type='str'),
            state=dict(type='str')
        )
    )

    username = module.params['username']
    password = module.params['password']
    state = module.params['state']

    if state == 'absent':
        if not username:
            module.exit_json(changed=False, failed=True,
                             msg="Username not provided")
        ls_users_cmd = build_cmd(module, "-l")
        (rc, out, err) = module.run_command(ls_users_cmd)
        if username in out:
            cmd = build_cmd(module, '--deleteUser', username)
            (rc, out, err) = module.run_command(cmd)
            if rc is not None and rc != 0:
                return module.fail_json(msg=err)
            module.exit_json(changed=True, msg="User deleted")
        else:
            module.exit_json(changed=False, msg="No such user exists")
    elif state == 'present':
        if not username or not password:
            module.exit_json(changed=False, failed=True,
                             msg="Username or password not provided")
        ls_users_cmd = build_cmd(module, "-l")
        (rc, out, err) = module.run_command(ls_users_cmd)
        if rc is not None and rc != 0:
            return module.fail_json(msg=err)

        if username in out:
            module.exit_json(changed=False, msg="User already exists")
        else:
            cmd = build_cmd(module, '--newUser', username, '-p', password)
            (rc, out, err) = module.run_command(cmd)
            if rc is not None and rc != 0:
                return module.fail_json(msg=err)
            module.exit_json(changed=True, msg="User added")
    elif state == 'list':
        ls_users_cmd = build_cmd(module, "-l")
        (rc, out, err) = module.run_command(ls_users_cmd)
        if rc is not None and rc != 0:
            return module.fail_json(msg=err)
        users = out.split('\n')
        if users[0] == 'User names:':
            users.pop(0)
        module.exit_json(changed=False, msg=users)
    elif state == 'update':
        if not username or not password:
            module.exit_json(changed=False, failed=True,
                             msg="Username or password not provided")
        cmd = build_cmd(module, "--cu", username, '-p', password)
        (rc, out, err) = module.run_command(cmd)
        if rc is not None and rc != 0:
            return module.fail_json(msg=err)
        module.exit_json(changed=True, msg="Password changed")
    else:
        module.exit_json(changed=False, msg="No state specified")


if __name__ == '__main__':
    main()
