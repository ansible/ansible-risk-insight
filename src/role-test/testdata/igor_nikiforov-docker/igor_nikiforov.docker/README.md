# Ansible Role: Docker

This role install and configures Docker as well as compose and Docker SDK for Python.

## Requirements

This role developed and tested with following Ansible versions:

| Name                                                   | Version         |
|--------------------------------------------------------|-----------------|
| [ansible](https://pypi.org/project/ansible-base/)      | ```>= 2.9.13``` |
| [ansible-base](https://pypi.org/project/ansible-base/) | ```>= 2.10.1``` |
| [ansible-core](https://pypi.org/project/ansible-core/) | ```>= 2.11.2``` |

Other Ansible versions was not tested but will probably work.

## Installation

Use ```ansible-galaxy install igor_nikiforov.docker``` to install the latest stable release of role.

You could also install it from requirements ```ansible-galaxy install -r requirements.yml```:

```yaml
# requirements.yml
---
roles:
  - name: igor_nikiforov.docker
    version: v1.1.0
```

## Platforms

| Name   | Version             |
|--------|---------------------|
| Debian | ```buster```        |
| Ubuntu | ```focal, groovy``` |
| CentOS | ```7.4+, 8```       |
| RedHat | ```7.4+, 8```       |

Other OS distributions was not tested but will probably work. In case if not please raise a PR!

## Variables

| Name                                                                                                                                              | Description                                               | Default                                 |
|---------------------------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------|-----------------------------------------|
| <a name="docker_supported_architectures"></a> [docker_supported_architectures](#variable\_docker_supported_architectures)                         | List of Docker supported architectures                    | `["x86_64", "arm64", "armhf", "s390x"]` |
| <a name="docker_install"></a> [docker_install](#variable\_docker_install)                                                                         | If True, Docker will be installed                         | `true`                                  |
| <a name="docker_version"></a> [docker_version](#variable\docker_version)                                                                          | Docker version                                            | `latest`                                |
| <a name="docker_bash_completion_install"></a> [docker_bash_completion_install](#variable\_docker_bash_completion_install)                         | If True, Docker bash completion will be installed         | `true`                                  |
| <a name="docker_daemon_config"></a> [docker_daemon_config](#variable\_docker_daemon_config)                                                       | Docker daemon configuration                               | `{}`                                    |
| <a name="docker_service_enabled"></a> [docker_service_enabled](#variable\_docker_service_enabled)                                                 | Whether Docker service should start on boot               | `true`                                  |
| <a name="docker_service_state"></a> [docker_service_state](#variable\_docker_service_state)                                                       | State of Docker service                                   | `started`                               |
| <a name="docker_users"></a> [docker_users](#variable\_docker_users)                                                                               | List of users to be added to docker group                 | `[]`                                    |
| <a name="docker_sdk_for_python_install"></a> [docker_sdk_for_python_install](#variable\_docker_sdk_for_python_install)                            | If True, Docker SDK for Python will be installed          | `false`                                 |
| <a name="docker_sdk_for_python_version"></a> [docker_sdk_for_python_version](#variable\_docker_sdk_for_python_version)                            | Docker SDK for Python version                             | `latest`                                |
| <a name="docker_compose_install"></a> [docker_compose_install](#variable\_docker_compose_install)                                                 | If True, Docker Compose will be installed                 | `false`                                 |
| <a name="docker_compose_version"></a> [docker_compose_version](#variable\_docker_compose_version)                                                 | Docker Compose version                                    | `latest`                                |
| <a name="docker_compose_bash_completion_install"></a> [docker_compose_bash_completion_install](#variable\_docker_compose_bash_completion_install) | If True, Docker Compose bash completion will be installed | `true`                                  |

## Usage

Role supports all Docker daemon configuration parameters which could be passed via ```docker_daemon_config``` variable. You could find example of JSON config format in [Docker official documentation](https://docs.docker.com/engine/reference/commandline/dockerd/#daemon-configuration-file). For usage in role you should convert config from JSON to YAML format, for example using [this online tool](https://www.json2yaml.com/).

### Examples

```yaml
# playbook.yml
---
- hosts: all
  become: True
  gather_facts: False

  pre_tasks:
    - wait_for_connection: { timeout: 300 }
    - setup:

  vars:
    docker_sdk_for_python_install: True
    docker_compose_install: True
    docker_daemon_config:
      default-address-pools:
        - { base: 172.16.0.0/16, size: 26 }
      log-driver: "json-file"
      log-opts:
        max-size: "10m"
        max-file: "3"

  tasks:
    - name: Install Docker
      import_role:
        name: docker
```

## License

MIT

## Author Information

[Igor Nikiforov](https://github.com/igor-nikiforov)
