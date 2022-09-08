#!/usr/bin/python
# Copyright (c) 2015 Hewlett-Packard Development Company, L.P.
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

DOCUMENTATION = '''
---
module: identity_user
short_description: Manage OpenStack Identity Users
author: OpenStack Ansible SIG
description:
    - Manage OpenStack Identity users. Users can be created,
      updated or deleted using this module. A user will be updated
      if I(name) matches an existing user and I(state) is present.
      The value for I(name) cannot be updated without deleting and
      re-creating the user.
options:
   name:
     description:
        - Username for the user
     required: true
     type: str
   password:
     description:
        - Password for the user
     type: str
   update_password:
     required: false
     choices: ['always', 'on_create']
     description:
        - C(always) will attempt to update password.  C(on_create) will only
          set the password for newly created users.
     type: str
   email:
     description:
        - Email address for the user
     type: str
   description:
     description:
        - Description about the user
     type: str
   default_project:
     description:
        - Project name or ID that the user should be associated with by default
     type: str
   domain:
     description:
        - Domain to create the user in if the cloud supports domains
     type: str
   enabled:
     description:
        - Is the user enabled
     type: bool
     default: 'yes'
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
# Create a user
- openstack.cloud.identity_user:
    cloud: mycloud
    state: present
    name: demouser
    password: secret
    email: demo@example.com
    domain: default
    default_project: demo

# Delete a user
- openstack.cloud.identity_user:
    cloud: mycloud
    state: absent
    name: demouser

# Create a user but don't update password if user exists
- openstack.cloud.identity_user:
    cloud: mycloud
    state: present
    name: demouser
    password: secret
    update_password: on_create
    email: demo@example.com
    domain: default
    default_project: demo

# Create a user without password
- openstack.cloud.identity_user:
    cloud: mycloud
    state: present
    name: demouser
    email: demo@example.com
    domain: default
    default_project: demo
'''


RETURN = '''
user:
    description: Dictionary describing the user.
    returned: On success when I(state) is 'present'
    type: complex
    contains:
        default_project_id:
            description: User default project ID. Only present with Keystone >= v3.
            type: str
            sample: "4427115787be45f08f0ec22a03bfc735"
        domain_id:
            description: User domain ID. Only present with Keystone >= v3.
            type: str
            sample: "default"
        email:
            description: User email address
            type: str
            sample: "demo@example.com"
        id:
            description: User ID
            type: str
            sample: "f59382db809c43139982ca4189404650"
        name:
            description: User name
            type: str
            sample: "demouser"
'''

from ansible_collections.openstack.cloud.plugins.module_utils.openstack import OpenStackModule


class IdentityUserModule(OpenStackModule):
    argument_spec = dict(
        name=dict(required=True),
        password=dict(required=False, default=None, no_log=True),
        email=dict(required=False, default=None),
        default_project=dict(required=False, default=None),
        description=dict(type='str'),
        domain=dict(required=False, default=None),
        enabled=dict(default=True, type='bool'),
        state=dict(default='present', choices=['absent', 'present']),
        update_password=dict(default=None, choices=['always', 'on_create']),
    )

    module_kwargs = dict()

    def _needs_update(self, params_dict, user):
        for k in params_dict:
            if k not in ('password', 'update_password') and user[k] != params_dict[k]:
                return True

        # We don't get password back in the user object, so assume any supplied
        # password is a change.
        if (
            params_dict['password'] is not None
            and params_dict['update_password'] == 'always'
        ):
            return True

        return False

    def _get_domain_id(self, domain):
        try:
            # We assume admin is passing domain id
            domain_id = self.conn.get_domain(domain)['id']
        except Exception:
            # If we fail, maybe admin is passing a domain name.
            # Note that domains have unique names, just like id.
            try:
                domain_id = self.conn.search_domains(filters={'name': domain})[0]['id']
            except Exception:
                # Ok, let's hope the user is non-admin and passing a sane id
                domain_id = domain

        return domain_id

    def _get_default_project_id(self, default_project, domain_id):
        project = self.conn.get_project(default_project, domain_id=domain_id)
        if not project:
            self.fail_json(msg='Default project %s is not valid' % default_project)

        return project['id']

    def run(self):
        name = self.params['name']
        password = self.params.get('password')
        email = self.params['email']
        default_project = self.params['default_project']
        domain = self.params['domain']
        enabled = self.params['enabled']
        state = self.params['state']
        update_password = self.params['update_password']
        description = self.params['description']

        domain_id = None
        if domain:
            domain_id = self._get_domain_id(domain)
            user = self.conn.get_user(name, domain_id=domain_id)
        else:
            user = self.conn.get_user(name)

        if state == 'present':
            if update_password in ('always', 'on_create'):
                if not password:
                    msg = "update_password is %s but a password value is missing" % update_password
                    self.fail_json(msg=msg)
            default_project_id = None
            if default_project:
                default_project_id = self._get_default_project_id(
                    default_project, domain_id)

            if user is None:
                if description is not None:
                    user = self.conn.create_user(
                        name=name, password=password, email=email,
                        default_project=default_project_id, domain_id=domain_id,
                        enabled=enabled, description=description)
                else:
                    user = self.conn.create_user(
                        name=name, password=password, email=email,
                        default_project=default_project_id, domain_id=domain_id,
                        enabled=enabled)
                changed = True
            else:
                params_dict = {'email': email, 'enabled': enabled,
                               'password': password,
                               'update_password': update_password}
                if description is not None:
                    params_dict['description'] = description
                if domain_id is not None:
                    params_dict['domain_id'] = domain_id
                if default_project_id is not None:
                    params_dict['default_project_id'] = default_project_id

                if self._needs_update(params_dict, user):
                    if update_password == 'always':
                        if description is not None:
                            user = self.conn.update_user(
                                user['id'], password=password, email=email,
                                default_project=default_project_id,
                                domain_id=domain_id, enabled=enabled, description=description)
                        else:
                            user = self.conn.update_user(
                                user['id'], password=password, email=email,
                                default_project=default_project_id,
                                domain_id=domain_id, enabled=enabled)
                    else:
                        if description is not None:
                            user = self.conn.update_user(
                                user['id'], email=email,
                                default_project=default_project_id,
                                domain_id=domain_id, enabled=enabled, description=description)
                        else:
                            user = self.conn.update_user(
                                user['id'], email=email,
                                default_project=default_project_id,
                                domain_id=domain_id, enabled=enabled)
                    changed = True
                else:
                    changed = False
            self.exit_json(changed=changed, user=user)

        elif state == 'absent':
            if user is None:
                changed = False
            else:
                if domain:
                    self.conn.delete_user(user['id'], domain_id=domain_id)
                else:
                    self.conn.delete_user(user['id'])
                changed = True
            self.exit_json(changed=changed)


def main():
    module = IdentityUserModule()
    module()


if __name__ == '__main__':
    main()
