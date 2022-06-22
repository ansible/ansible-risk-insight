==========================================
Scenario - Configuring keystone federation
==========================================

Federation for keystone can be utilised in two ways:

* Supporting keystone as a Service Provider (SP): consuming identity
  assertions issued by an external Identity Provider, such as SAML
  assertions or OpenID Connect claims.
* Supporting keystone as an Identity Provider (IdP): fulfilling authentication
  requests on behalf of Service Providers.

  .. important::

      It is also possible to have one keystone act as an SP that
      consumes Identity from another keystone acting as an IdP.
      This will be discussed further in this document.

In keystone federation, the IdP and SP exchange information securely to
enable a user on the IdP cloud to access resources of the SP cloud.

The following procedure describes how to set up federation:

#. Configure keystone SPs.
#. Configure the IdP:

   * Configure keystone as an IdP.
   * Configure Active Directory Federation Services (ADFS) 3.0 as an IdP.

#. Configure the service provider:

   * Configure keystone as a federated service provider.
   * Configure keystone mappings.

#. Run the authentication wrapper to use keystone-as-a-Service-Provider
   federation.

.. toctree::

   configure-federation-wrapper
   configure-federation-sp.rst
   configure-federation-idp.rst
   configure-federation-mapping.rst
