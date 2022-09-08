===========================================
Configuring keystone-to-keystone federation
===========================================

In keystone-to-keystone federation (k2k), the IdP and SP
keystone instances exchange information securely to enable a user on
the IdP cloud to access resources of the SP cloud.

.. important::

   This section applies only to federation between keystone IdP
   and keystone SP. It does not apply to non-keystone IdP.

The k2k authentication flow involves the following steps:

#. Log in to the IdP with your credentials.
#. Send a request to the IdP to generate an assertion for a given SP.
#. Submit the assertion to the SP on the configured ``sp_url``
   endpoint. The Shibboleth service running on the SP receives the assertion
   and verifies it. If it is valid, a session with the client starts and
   returns the session ID in a cookie.
#. Connect to the SP on the configured ``auth_url`` endpoint,
   providing the Shibboleth cookie with the session ID. The SP responds with
   an unscoped token that you use to access the SP.
#. You connect to the keystone service on the SP with the unscoped
   token, and the desired domain and project, and receive a scoped token
   and the service catalog.
#. With your token, you can now make API requests to the endpoints in the
   catalog.

Keystone-to-keystone federation authentication wrapper
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The following steps above involve manually sending API requests.

.. note::

   The infrastructure for the command line utilities that performs these steps
   for the user does not exist.

To obtain access to a SP cloud, OpenStack-Ansible provides a script that wraps
the above steps. The script is called ``federated-login.sh`` and is
used as follows:

.. code::

   # ./scripts/federated-login.sh -p project [-d domain] sp_id

* ``project`` is the project in the SP cloud that you want to access.
* ``domain`` is the domain in which the project lives (the default domain is
  used if this argument is not given).
* ``sp_id`` is the unique ID of the SP. This is given in the IdP configuration.

The script outputs the results of all the steps in the authentication flow to
the console. At the end, it prints the available endpoints from the catalog
and the scoped token provided by the SP.

Use the endpoints and token with the openstack command line client as follows:

.. code::

   # openstack --os-token=<token> --os-url=<service-endpoint> [options]

Or, alternatively:

.. code::

   # export OS_TOKEN=<token>
   # export OS_URL=<service-endpoint>
   # openstack [options]

Ensure you select the appropriate endpoint for your operation.
For example, if you want to work with servers, the ``OS_URL``
argument must be set to the compute endpoint.

.. note::

   At this time, the OpenStack client is unable to find endpoints in
   the service catalog when using a federated login.
