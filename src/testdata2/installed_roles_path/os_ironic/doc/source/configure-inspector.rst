================================================================
Configuring the Bare Metal (ironic) inspector service (optional)
================================================================

.. note::

   This feature is experimental at this time and it has not been fully
   production tested yet.

Ironic Inspector is an Ironic service that deploys a tiny image called
ironic-python-agent that gathers information about a Bare Metal node. The data
is then stored in the database for further use later. The node is then updated
with properties based in the introspection data.

The inspector configuration requires some pre-deployment steps to allow the
Ironic playbook to make the inspector functioning.

Networking
~~~~~~~~~~
Ironic networking must be configured as normally done. The inspector and
Ironic will both share the TFTP server.

Networking will depend heavily on your environment. For example, the DHCP for
both Ironic and inspector will come from the same subnet and will be a subset
of the typical ironic allocated range.


Required Overrides
~~~~~~~~~~~~~~~~~~
  .. code-block::

     # names of your ironic-python-agent initrd/kernel images
     ironic_inspector_ipa_initrd_name: ironic-deploy.initramfs
     ironic_inspector_ipa_kernel_name: ironic-deploy.vmlinuz

     # dnsmasq/dhcp information for inspector
     ironic_inspector_dhcp_pool_range: <START> <END> (subset of ironic IPs)
     ironic_inspector_dhcp_subnet: <IRONIC SUBNET CIDR>
     ironic_inspector_dhcp_subnet_mask: 255.255.252.0
     ironic_inspector_dhcp_gateway: <IRONIC GATEWAY>
     ironic_inspector_dhcp_nameservers: 8.8.8.8
