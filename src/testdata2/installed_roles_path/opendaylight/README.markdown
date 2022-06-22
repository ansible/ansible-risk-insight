[![CI Status][7]][6]

# OpenDaylight Ansible Role

Ansible role for the [OpenDaylight SDN controller][1].

#### Ansible Dependencies: `ansible-galaxy`

Releases of this role can also be installed available via [Ansible Galaxy][5]
which ships with Ansible.

To install the latest version of ansible on RedHat based OSs:

```
$ sudo yum install -y ansible
```

To install the latest version of ansible on Debian based OSs:

```
$ sudo apt-add-repository ppa:ansible/ansible
$ sudo apt-get update
$ sudo apt-get install -y ansible
```

#### Ansible Dependencies: Roles

After you install the `ansible-galaxy` tool, point it at the project's
`requirements.yml` file to install ODL's role.

```
[~/ansible-opendaylight]$ ansible-galaxy install -r requirements.yml
```

The OpenDaylight Ansible role doesn't depend on any other Ansible roles.

## Role Variables

### Karaf Features

To set extra Karaf features to be installed at OpenDaylight start time,
pass them in a list to the `extra_features` variable. The extra features
you pass will typically be driven by the requirements of your ODL install.
You'll almost certainly need to pass some.

OpenDaylight normally installs a default set of Karaf features at boot.
They are recommended, so the ODL Ansible role defaults to installing them.
This can be customized by overriding the `default_features` variable. You
shouldn't normally need to do so.

### REST API Port

To change the port on which OpenDaylight's northbound listens for REST API
calls, use the `nb_rest_port` variable. This was added because OpenStack's
Swift project uses a conflicting port.

The Ansible role will handle opening this port in FirewallD if it's active.

### Install Method

OpenDaylight can be installed either via an RPM or a .deb depending on the operating system.
For RedHat based OSs, the valid options for `odl_install_method` are `rpm_repo` or `rpm_path`.
For Debian based OSs, `odl_install_method` can accept either `deb_repo` or `deb_path`.

## Installing OpenDaylight

To install OpenDaylight on your system, you can make use of `ansible-playbook`.

On RedHat based OSs, you can install OpenDaylight from RPM repo (recommended) using
the playbook `examples/all_defaults_playbook.yml` or from a local/remote path to an ODL rpm via
`examples/rpm_path_install_playbook.yml`.

```Shellsession
sudo ansible-playbook -i "localhost," -c local examples/<playbook>
```

On a Debian based OS, you can install OpenDaylight either from a Debian repo using the
playbook `examples/deb_repo_install_playbook.yml` or from a local/remote Deb path using
`examples/deb_path_install_playbook.yml`.

```Shellsession
sudo ansible-playbook -i "localhost," -c local examples/<playbook>
```

You can also use ansible-opendaylight using [Vagrant base box examples of Ansible ODL deployments][8].

## Example Playbook

The simple example playbook below would install and configure OpenDaylight
using this role.

```yaml
---
- hosts: example_host
  sudo: yes
  roles:
    - opendaylight
```

To override default settings, pass variables to the `opendaylight` role.

```yaml
---
- hosts: all
  sudo: yes
  roles:
    - role: opendaylight
      extra_features: ['odl-netvirt-openstack']
```

Results in:

```
opendaylight-user@root>feature:list | grep odl-netvirt-openstack
odl-netvirt-openstack | <odl-release> | x | odl-netvirt-<odl-release> | OpenDaylight :: NetVirt :: OpenStack
```

## License

The OpenDaylight Ansible role is Open Sourced under a BSD two-clause license.

[Contributions encouraged][4]!

## Author Information

[Daniel Farrell][2] of the [OpenDaylight Integration/Packaging project][3] is
the main developer of this role.

See [CONTRIBUTING.md][4] for details about how to contribute to the
OpenDaylight Ansible role.

[1]: http://www.opendaylight.org/project/technical-overview "OpenDaylight main technical overview"

[2]: https://wiki.opendaylight.org/view/User:Dfarrell07 "Maintainer information"

[3]: https://wiki.opendaylight.org/view/Integration/Packaging "OpenDaylight Integration/Packaging project wiki"

[4]: https://github.com/dfarrell07/ansible-opendaylight/blob/master/CONTRIBUTING.md "OpenDaylight Ansible role contributing docs"

[5]: https://galaxy.ansible.com/list#/roles/3948 "OpenDaylight Ansible role on Ansible Galaxy"

[6]: https://travis-ci.org/dfarrell07/ansible-opendaylight "OpenDaylight Ansible role Travis CI"

[7]: https://travis-ci.org/dfarrell07/ansible-opendaylight.svg "Travis CI status image"

[8]: https://github.com/dfarrell07/vagrant-opendaylight#ansible-deployments "Ansible Vagrant deployment"
