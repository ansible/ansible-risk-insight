===========================
Configure keystone mappings
===========================

The federated_identities functionality can be used to create
projects, groups, roles and domains before your federation attribute
mappings route users towards those resources. If you manage creation of
projects, groups, roles and domains via a separate mechanism making use
of federated_identities is not required.

.. code-block:: yaml

      federated_identities:
        - domain: default
          project: fedproject
          group: fedgroup
          role: _member_

#. ``project``: The project that federation users have access to.
   If the project does not already exist, create it in the
   domain with the name, ``domain``.

#. ``group``: The keystone group that federation users
   belong. If the group does not already exist, create it in
   the domain with the name, ``domain``.

#. ``role``: The role that federation users use in that project.
   Create the role if it does not already exist.

#. ``domain``: The domain where the ``project`` lives, and where
   the you assign roles. Create the domain if it does not already exist.
   This should be the ID of the domain.

Ansible implements the equivalent of the following OpenStack CLI commands:

.. code-block:: shell-session

  # if the domain does not already exist
  openstack domain create Default

  # if the group does not already exist
  openstack group create fedgroup --domain Default

  # if the role does not already exist
  openstack role create _member_

  # if the project does not already exist
  openstack project create --domain default fedproject

  # map the role to the project and user group in the domain
  openstack role add --project fedproject --group fedgroup _member_

To extend simply add more entries to the list.
For example:

.. code-block:: yaml

      federated_identities:
        - domain: default
          project: fedproject
          group: fedgroup
          role: _member_
        - domain: default
          project: fedproject2
          group: fedgroup2
          role: _member_

Keystone federation attribute mapping
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Attribute mapping adds a set of rules to map federation attributes to keystone
users and groups. IdP specifies one mapping per protocol.

Use mapping objects multiple times by different combinations of
IdP and protocol.

The details of how the mapping engine works, the schema, and various rule
examples are in the `keystone developer documentation
<https://docs.openstack.org/keystone/latest/advanced-topics/federation/federated_identity.html#mapping-combinations>`_.

For example, SP attribute mapping configuration for an ADFS IdP:

.. code-block:: yaml

      mapping:
        name: adfs-IdP-mapping
        rules:
          - remote:
              - type: upn
            local:
              - group:
                  name: fedgroup
                  domain:
                    name: Default
              - user:
                  name: '{0}'
      attributes:
        - name: 'http://schemas.xmlsoap.org/ws/2005/05/identity/claims/upn'
          id: upn

Each IdP for an SP needs to be set up with a mapping. This tells the SP how
to interpret the attributes provided to the SP from the IdP.

In this example, the IdP publishes the ``upn`` attribute. As this
is not in the standard Shibboleth attribute map (see
``/etc/shibboleth/attribute-map.xml`` in the keystone containers), the configuration
of the IdP has extra mapping through the ``attributes`` dictionary.

The ``mapping`` dictionary is a YAML representation similar to the
keystone mapping property which Ansible uploads. The above mapping
produces the following in keystone.

.. code-block:: shell-session

  root@aio1_keystone_container-783aa4c0:~# openstack mapping list
  +------------------+
  | ID               |
  +------------------+
  | adfs-IdP-mapping |
  +------------------+

  root@aio1_keystone_container-783aa4c0:~# openstack mapping show adfs-IdP-mapping
  +-------+---------------------------------------------------------------------------------------------------------------------------------------+
  | Field | Value                                                                                                                                 |
  +-------+---------------------------------------------------------------------------------------------------------------------------------------+
  | id    | adfs-IdP-mapping                                                                                                                      |
  | rules | [{"remote": [{"type": "upn"}], "local": [{"group": {"domain": {"name": "Default"}, "name": "fedgroup"}}, {"user": {"name": "{0}"}}]}] |
  +-------+---------------------------------------------------------------------------------------------------------------------------------------+

  root@aio1_keystone_container-783aa4c0:~# openstack mapping show adfs-IdP-mapping | awk -F\| '/rules/ {print $3}' | python -mjson.tool
  [
      {
          "remote": [
              {
                  "type": "upn"
              }
          ],
          "local": [
              {
                  "group": {
                      "domain": {
                          "name": "Default"
                      },
                      "name": "fedgroup"
                  }
              },
              {
                  "user": {
                      "name": "{0}"
                  }
              }
          ]
      }
  ]

The interpretation of the above mapping rule is that any federation user
authenticated by the IdP maps to an ``ephemeral`` user in keystone.
The user is a member of a group named ``fedgroup``. This is in a domain
called ``Default``. As we have specified the domain, the users
assignments in the keystone backend will be looked up alongside the
assignments made in the mapping.
The user's ID and Name (federation uses the same value for both properties)
for all OpenStack services is the value of ``upn``.
