# Ansible Role for Consul

This role installs and sets up Consul to connect to a Consul cluster.

## License

AGPLv3

## Role Variables

See `defaults/main.yml`.

## Dependencies

This depends on the 'nginx-proxy' role in the same repository.

## Usage

This role usually requires the `consul_ip`, `consul_nodename` variables to be set for each host. However, in AWS,
when EC2 instances are launched from an AMI or stopped and started, or use an elastic IP, their IP addresses will
likely change. So to allow automatic configuration of the `consul_ip`, `consul_nodename` variables
while generating the consul configuration, the `consul_auto_generate_config` flag can be set to a
truthy value.

When `consul_auto_generate_config` is set to a truthy value, a script which wraps the consul startup command is
set up in the consul services. It determines the EC2 instance's IP addresses (private and public) and
automatically generates the consul configuration file with the correct IP address and an appropriate,
unique node name.

The unique name is generated as `<value of consul_nodename>-<private IP address>-<public IP address>`, where
the `.` in the IP address values are replaced by `-`. After generating the correct configuration, the wrapper script
starts consul.

If the node was already in the cluster before and its IP address or node name has changed, the wrapper script
also cleans up the stale `node-id` file and allows the node to join the cluster as a new node.

Note that the automatic consul reconfiguration works only at the service startup time. So if an elastic IP address
was assigned/unassigned to an EC2 instance, the consul configuration will not be automatically updated till the
service is manually restarted. If the service is not restarted, this will cause the consul cluster to think that
the node is down as the old public IP address is still registered there and is now unreachable.
