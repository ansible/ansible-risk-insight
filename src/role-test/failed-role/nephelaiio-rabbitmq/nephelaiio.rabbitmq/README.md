# nephelaiio.rabbitmq

[![Build Status](https://travis-ci.org/nephelaiio/ansible-role-rabbitmq.svg?branch=master)](https://travis-ci.org/nephelaiio/ansible-role-rabbitmq)
[![Ansible Galaxy](http://img.shields.io/badge/ansible--galaxy-systemd--service-blue.svg)](https://galaxy.ansible.com/nephelaiio/rabbitmq/)

An [ansible role](https://galaxy.ansible.com/nephelaiio/rabbitmq) to install and configure rabbitmq

## Role Variables

Please refer to the [defaults file](/defaults/main.yml) for an up to date list of input parameters.

## Example Playbook

- hosts: servers
  roles:
     - role: rabbitmq
       rabbitmq_packages_state: latest


## Testing

Please make sure your environment has [docker](https://www.docker.com) installed in order to run role validation tests. Additional python dependencies are listed in the [requirements file](https://github.com/nephelaiio/ansible-role-requirements/blob/master/requirements.txt)

Role is tested against the following distributions (docker images):
  * Ubuntu Xenial
  * Ubuntu Bionic
  * CentOS 7
  * Debian Stretch
  * Arch Linux

You can test the role directly from sources using command ` molecule test `

## License

This project is licensed under the terms of the [MIT License](/LICENSE)
