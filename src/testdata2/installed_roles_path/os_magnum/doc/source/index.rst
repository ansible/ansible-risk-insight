========================
OpenStack-Ansible Magnum
========================

Ansible role that installs and configures OpenStack Magnum. Magnum is
installed behind the Apache webserver listening on port 9511 by default.


To clone or view the source code for this repository, visit the role repository
for `os_magnum <https://github.com/openstack/openstack-ansible-os_magnum>`_.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

To use this role, define the following variables:

.. code-block:: yaml

    # Magnum TCP listening port
    magnum_service_port: 9511

    # Magnum service protocol http or https
    magnum_service_proto: http

    # Magnum Galera address of internal load balancer
    magnum_galera_address: "{{ internal_lb_vip_address }}"

    # Magnum Galera database name
    magnum_galera_database_name: magnum_service

    # Magnum Galera username
    magnum_galera_user: magnum

    # Magnum rpc userid
    magnum_oslomsg_rpc_userid: magnum

    # Magnum rpc vhost
    magnum_oslomsg_rpc_vhost: /magnum

    # Magnum notify userid
    magnum_oslomsg_notify_userid: magnum

    # Magnum notify vhost
    magnum_oslomsg_notify_vhost: /magnum

This list is not exhaustive. See role internals for further details.

Wiring docker with cinder
~~~~~~~~~~~~~~~~~~~~~~~~~

If you need to use volumes, default_docker_volume_type should be set.
By default, Magnum doesn't need one.

To deploy Magnum with cinder integration, please set the following
in your ``/etc/openstack_deploy/user_variables.yml``:

.. code-block:: yaml

    magnum_config_overrides:
      cinder:
        default_docker_volume_type: lvm

If you have defined cinder_default_volume_type for all your nodes,
by defining it in your user_variables, you can re-use it directly:

.. code-block:: yaml

    magnum_config_overrides:
      cinder:
        default_docker_volume_type: "{{ cinder_default_volume_type }}"

Example playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Tags
~~~~

This role supports two tags: ``magnum-install`` and ``magnum-config``.
The ``magnum-install`` tag can be used to install and upgrade. The
``magnum-config`` tag can be used to maintain configuration of the
service.

Post-deployment configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Deploying the magnum service makes the API components available to use.
Additional configuration is required to make a working Kubernetes cluster,
including loading the correct Image and setting up a suitable Cluster Template

This example is intended to show the steps required and should be updated
as needed for the version of k8s and associated components. The example has
been tested by a deployer with magnum SHA
fe35af8ef5d9e65a4074aa3ba3ed3116b7322415.

First, upload the coreos image. this can be done either manually or using
the os_magnum playbooks.

Manual configuration:

.. code-block:: bash

    wget https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/32.20201004.3.0/x86_64/fedora-coreos-32.20201004.3.0-openstack.x86_64.qcow2.xz

    (convert to raw if necessary here for ceph backed storage)

    openstack image create "fedora-coreos-latest" --disk-format raw --container-format bare \
    --file fedora-coreos-32.20201004.3.0-openstack.x86_64.raw --property os_distro='fedora-coreos'

Via os_magnum playbooks and data in user_variables.yml

.. code-block:: yaml

   magnum_glance_images:
    - name: fedora-coreos-latest
      disk_format: qcow2
      image_format: bare
      public: true
      file: https://builds.coreos.fedoraproject.org/prod/streams/stable/builds/31.20200210.3.0/x86_64/fedora-coreos-31.20200210.3.0-openstack.x86_64.qcow2.xz
      distro: "coreos"
      checksum: "sha256:9a5252e24b82a5edb1ce75b05653f59895685b0f1028112462e908a12deae518"


Second, create the cluster template.

Manual configuration:

.. code-block:: bash

    openstack coe cluster template create <name> --coe kubernetes --external-network <ext-net> \
    --image "fedora-coreos-latest" --master-flavor <flavor> --flavor <flavor> --master-lb-enabled \
    --docker-volume-size 50 --network-driver calico --docker-storage-driver overlay2 \
    --volume-driver cinder \
    --labels boot_volume_type=<your volume type>,boot_volume_size=50,kube_tag=v1.18.6,availability_zone=nova,helm_client_url="https://get.helm.sh/helm-v3.4.0-linux-amd64.tar.gz",helm_client_sha256="270acb0f085b72ec28aee894c7443739271758010323d72ced0e92cd2c96ffdb",helm_client_tag="v3.4.0",etcd_volume_size=50,auto_scaling_enabled=true,auto_healing_enabled=true,auto_healing_controller=magnum-auto-healer,etcd_volume_type=<your volume type>,kube_dashboard_enabled=True,monitoring_enabled=True,ingress_controller=nginx,cloud_provider_tag=v1.19.0,magnum_auto_healer_tag=v1.19.0,container_infra_prefix=<docker-registry-without-rate-limit> -f yaml -c uuid

The equivalent Cluster Template configuration through os_magnum and data in
user_variables.yml

.. code-block:: yaml

    magnum_cluster_templates:
      - name: <name>
        coe: kubernetes
        external_network_id: <network-id>
        image_id: <image-id>
        master_flavor_id: <master-flavor-id>
        flavor_id: <minon-flavor-id>
        master_lb_enabled: true
        docker_volume_size: 50
        network_driver: calico
        docker_storage_driver: overlay2
        volume_driver: cinder
        labels:
          boot_volume_type: <your volume type>
          boot_volume_size: 50
          kube_tag: v1.18.6
          availability_zone: nova
          helm_client_url: "https://get.helm.sh/helm-v3.4.0-linux-amd64.tar.gz"
          helm_client_sha256: "270acb0f085b72ec28aee894c7443739271758010323d72ced0e92cd2c96ffdb"
          helm_client_tag: v3.4.0
          etcd_volume_size: 50
          auto_scaling_enabled: true
          auto_healing_enabled: true
          auto_healing_controller: magnum-auto-healer
          etcd_volume_type: <your volume type>
          kube_dashboard_enabled: True
          monitoring_enabled: True
          ingress_controller: nginx
          cloud_provider_tag: v1.19.0
          magnum_auto_healer_tag: v1.19.0
          container_infra_prefix: <docker-registry-without-rate-limit>

Note that openstack-ansible deploys the Magnum API service. It is not in scope
for openstack-ansible to maintain a guaranteed working cluster template as this
will vary depending on the precise version of Magnum deployed and the required
version of k8s and it's dependancies.

It will be necessary to specify a docker registry (potentially hosting your own
mirror or cache) which does not enforce rate limits when deploying Magnum in a
production environment.

Post-deployment debugging
~~~~~~~~~~~~~~~~~~~~~~~~~

If the k8s cluster does not create properly, or times out during creation, then
the cloud-init logs in the master/minion nodes should be examined, also check
the heat-config log and heat-container-agent status.
