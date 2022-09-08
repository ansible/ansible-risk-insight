.. Copyright (C) 2017 Maciej Delmanowski <drybjed@gmail.com>
.. Copyright (C) 2017 DebOps <https://debops.org/>
.. SPDX-License-Identifier: GPL-3.0-only

Description
===========

`Cyrus SASL library <https://www.cyrusimap.org/sasl/>`_ is
part of the Cyrus IMAP project and can be used to authenticate access to
different services that implement
`Simple Authentication Security Layer <https://en.wikipedia.org/wiki/Simple_Authentication_and_Security_Layer>`_
support.

This role allows configuration of multiple :command:`saslauthd` instances which
can be used by different services. By default role can configure support for
SMTP AUTH for Postfix, other services might be supported in the future. The
role is also integrated with the LDAP framework implemented in the
:ref:`debops.ldap` role and can be used to implement authentication via the
LDAP directory in other services.
