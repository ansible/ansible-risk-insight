.. Copyright (C) 2015      Nick Janetakis <nickjanetakis@gmail.com>
.. Copyright (C) 2016-2019 Maciej Delmanowski <drybjed@gmail.com>
.. Copyright (C) 2015-2019 DebOps <https://debops.org/>
.. SPDX-License-Identifier: GPL-3.0-only

Description
===========

`Go`__ is a compiled programming language similar to `C`__. Applications
written in Go are compiled to static binaries, with an aim to simplify
deployment. Many popular data center applications and tools are written in Go.

.. __: https://en.wikipedia.org/wiki/Go_(programming_language)
.. __: https://en.wikipedia.org/wiki/C_(programming_language)

The ``debops.golang`` role was designed to support multiple ways of deploying
Go applications using Ansible:

- installation from an APT package, when available;
- installation from source by cloning the application repositories and building
  the binaries in situ;
- installation of a precompiled binary downloaded from a remote source;

Installation via APT packages is a preferred method, since this saves compile
time and does not require access to third-party services. The other
installation methods can be used when a given Go application is not available
in a given OS release, or the upstream does not provide APT repositories.

The ``debops.golang`` role should be used as a dependent Ansible role in other
role playbooks, to simplify installation of the Go applications. Further
service configuration should be done in a given application role. Usage via the
Ansible inventory is, of course, still possible but might not be optimal.
