# consul-template

A role to install and set up up the [`consul-template`](https://github.com/hashicorp/consul-template) binary.

Note: this only installs the binary, and does not set up any sort of daemon.
It is primarily meant to be a dependent role by services that need to utilize consul-template in their own ways.
