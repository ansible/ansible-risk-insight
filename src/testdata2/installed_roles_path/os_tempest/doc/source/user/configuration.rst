========================
os_tempest configuration
========================

This page shows all of the variables which can be set in order to control
the behaviour of ``os_tempest`` role and provides examples on how to do so.

For a list of all variables with a default value set, please, refer to
the `this page`_.

.. _this page: ./default.html


Set the name of the cloud
-------------------------

``os-tempest`` uses named cloud credentials so it requires the name of the
cloud the role will be executed against. The name is provided to
``os-tempest`` via the ``tempest_cloud_name`` variable.
In order to use named clouds a ``clouds.yaml`` file needs to be present on the
**target host**. ``clouds.yaml`` file needs to be stored at one of the
supported locations,
`see here <https://docs.openstack.org/os-client-config/latest/user/configuration.html#config-files>`_
For more information about named clouds, please, follow to the
`os-client-config official documentation <https://docs.openstack.org/os-client-config/latest/user/index.html>`_

.. warning::

    ``clouds.yaml`` file has to be present on the target host - the host
    ``os_tempest`` is gonna be executed against.

Resource creation
-------------------------

Tempest requires some openstack resources(like flavors and images) in order to
function properly.
It is possible to choose which resources should be created or to skip resource
creation at all.
Below example shows how to use already existing public network and images.

.. code-block:: yaml

    tempest_default_role_resources: true
    tempest_public_net_create: false
    tempest_neutron_public_network_id: <network_id>
    tempest_images_create: false
    tempest_glance_image_id_1: <image_id>
    tempest_glance_image_id_2: <image_id>

python-tempestconf
------------------

python-tempestconf is a tool which generates a ``tempest.conf`` file necessary
for Tempest execution. For more information about the tool, please,
`follow its official documentation <https://docs.opendev.org/openinfra/python-tempestconf/latest/>`_.

If you want ``os_tempest`` to execute ``python-tempestconf``, prior to Tempest
execution in order to generate ``tempest.conf`` file, set
*tempest_use_tempestconf* variable to true:

.. code-block:: yaml

    tempest_use_tempestconf: true

More information about ``python-tempestconf`` arguments can
`be found here <https://docs.opendev.org/openinfra/python-tempestconf/latest/cli/cli_options.html>`_.

The best way how to pass any arguments to ``python-tempestconf`` is using its
`profile feature <https://docs.opendev.org/openinfra/python-tempestconf/latest/user/profile.html>`_.

``os_tempest`` provides *tempest_tempestconf_profile* variable for setting
desired python-tempestconf's arguments.
For example, if you wanted to define **debug** to *true*, **os-cloud** to
*demo* and override output of ``python-tempestconf`` to
``/my/location/tempest.conf``, it would be done by:

.. code-block:: yaml

    tempest_tempestconf_profile:
      debug: true
      os-cloud: demo
      out: /my/location/tempest.conf
