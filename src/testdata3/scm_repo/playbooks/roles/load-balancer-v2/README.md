# Load Balancer v2

This is a role to install a Load Balancer that utilizes Consul to help dynamically load configuration.

It depends upon external services to load certain key-value paths in Consul which consul-template
will watch for changes on. For any change, an atomic update to HAProxy's configuration file(s) will
be made, and HAProxy reloaded live.
