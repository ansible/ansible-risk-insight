# Changelog

## 1.3.0 (November 11th, 2021)

BUG FIXES:

* Fixed bash completion install for Docker Compose (```docker_compose_bash_completion_install```).
* Added linters and fixed all related lint issues.

## 1.2.0 (September 9th, 2021)

CHANGES:

* Support for bash completion in Docker (```docker_bash_completion_install```) and Docker Compose (```docker_compose_bash_completion_install```).
* Added names to each include_tasks in main task for more readability.

BUG FIXES:

* Fixed ```when``` condition in RHEL version detection.

## 1.1.0 (August 9th, 2021)

CHANGES:

* Docker SDK for Python (```docker_sdk_for_python_install```) is now disabled by default.
* Added systemd settings support - ```docker_service_enabled``` and ```docker_service_state```.
* Moved from generic ```package``` module to OS specific - ```apt``` and ```yum / dnf```.

BUG FIXES:

* Fix handler name to avoid error when using ```docker_daemon_config``` variable.
* Fixed repo file name when using RHEL.
* Checked and fixed YAML syntax with ```yamllint```.

## 1.0.0 (November 17th, 2020)

CHANGES:

* Initial release! 🎉
