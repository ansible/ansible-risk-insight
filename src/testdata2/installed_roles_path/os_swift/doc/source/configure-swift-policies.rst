`Home <index.html>`_ OpenStack-Ansible Swift

Storage policies
================

Storage policies allow segmenting the cluster for various purposes
through the creation of multiple object rings. Using policies, different
devices can belong to different rings with varying levels of
replication. By supporting multiple object rings, swift can
segregate the objects within a single cluster.

Use storage policies for the following situations:

-  Differing levels of replication: A provider may want to offer 2x
   replication and 3x replication, but does not want to maintain two
   separate clusters. They can set up a 2x policy and a 3x policy and
   assign the nodes to their respective rings.

-  Improving performance: Just as solid state drives (SSD) can be used
   as the exclusive members of an account or database ring, an SSD-only
   object ring can be created to implement a low-latency or high
   performance policy.

-  Collecting nodes into groups: Different object rings can have
   different physical servers so that objects in specific storage
   policies are always placed in a specific data center or geography.

-  Differing storage implementations: A policy can be used to direct
   traffic to collected nodes that use a different disk file (for
   example: Kinetic, GlusterFS).

Most storage clusters do not require more than one storage policy. The
following problems can occur if using multiple storage policies per
cluster:

-  Creating a second storage policy without any specified drives (all
   drives are part of only the account, container, and default storage
   policy groups) creates an empty ring for that storage policy.

-  Only use a non-default storage policy if specified when creating
   a container, using the ``X-Storage-Policy: <policy-name>`` header.
   After creating the container, it uses the storage policy.
   Other containers continue using the default or another specified
   storage policy.

For more information about storage policies, see: `Storage
Policies <https://docs.openstack.org/swift/latest/overview_policies.html>`_

