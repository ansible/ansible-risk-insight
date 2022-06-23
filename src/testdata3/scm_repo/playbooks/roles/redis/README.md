# Ansible role for deploying Redis

This role deploys [Redis](https://redis.io/) as a single instance, not in cluster.

This role uses DavidWittman's [redis role](https://galaxy.ansible.com/DavidWittman/redis) as that provides master-slave replication and sentinel out of the box.

## Deployment

The role can be run against a server with a vanilla Ubuntu 20.04 image.
