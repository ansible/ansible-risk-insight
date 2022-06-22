========================
Team and repository tags
========================

.. image:: https://governance.openstack.org/tc/badges/ansible-role-python_venv_build.svg
    :target: https://governance.openstack.org/tc/reference/tags/index.html

.. Change things from this point on

===================================
OpenStack-Ansible python_venv_build
===================================

This Ansible role prepares a python venv for use within the OpenStack-Ansible
project, but it may be used for other projects as well.

The role requires the following to be present prior to execution:

* virtualenv >= 1.10 (to support using the never-download option)
* pip >= 7.1 (to support using the constraints option) in the virtualenv
  once it has been created.

Use-cases
~~~~~~~~~

This role is built for the following use-cases:

1. Using a build host (a.k.a. repo server):

   * Build `python wheels`_ on a repo server with a given list of python
     packages.
   * Prepare a requirements.txt and constraints.txt file on the repo server,
     and use them to ensure that the build and installation processes are
     both consistent and idempotent.
   * On the build host, install the distribution packages required at build
     time.
   * On any number of target hosts, create a virtualenv and install these
     built wheels into it using the pip ``--find-links`` option.
   * On any number of target hosts, install the distribution packages required
     at run time.
   * Re-use previously built wheels to speed up any subsequent builds..

2. Not using a build host:

   * On any number of target hosts, create a virtualenv, then locally install
     the distribution packages required at build and run time, then locally
     compile and install the given list of python packages.
   * This negates the need for a repo server, but takes longer due to the
     increased number of dependencies to install and the compilation happening
     on every target host.
   * The only situation where a build host provides no benefit is where there
     is only a single target host (with no containers) and none of the packages
     installed into the venv will be used again for any other venvs built by
     this role on the same host.

It may be useful to review the `Python Build/Install Process Simplification`_
specification to understand the background that led to the creation of this
role.

.. _python wheels: https://pythonwheels.com
.. _Python Build/Install Process Simplification: https://specs.openstack.org/openstack/openstack-ansible-specs/specs/queens/python-build-install-simplification.html

Process
~~~~~~~

1. Pre-requisites are checked.

2. If wheel building is enabled, and there is a repo server in the environment,
   then the following happens on the repo server:

   a. The distribution packages required to execute the python wheel compile
      are installed.
   b. A set of requirements and source-constraints for the venv are compiled
      for pip to use when building the wheels. These are also used to determine
      whether there are changes to either for the purpose of idempotence.
   c. The python wheels are compiled, and an install-time constraints file is
      created. The install-time constraints file has the list of python
      packages with their versions - this differs from the source-constraints
      which may contain git SHA's.

3. The installation of the python packages then commences on the target hosts:

   a. If the wheel build was enabled:

      i. Only the distribution packages required at runtime by the python
         packages are installed.
      ii. A python venv is created at ``venv_install_destination_path``.
      iii. The requirements and constraints files for the venv are prepared in
           the venv path.
      iv. The python packages are installed from the wheels on the repo server
          using pip's ``--find-links`` option to ensure that they are preferred
          above the default pypi index.
      v. If there are any ``venv_packages_to_symlink`` then the appropriate
         python libraries installed into the system from those packages will be
         symlinked into the virtualenv. This provides for python libraries
         which have a tight coupling with C bindings which may not be portable
         as a wheel.

   b. If the wheel build was *not* enabled:

      i. The distribution packages required for compiling and at runtime by the
         python packages are installed.
      ii. A python venv is created at ``venv_install_destination_path``.
      iii. The requirements and constraints files for the venv are prepared in
           the venv path. The constraints file in this case would contain the
           same content as the source-constraints file on the repo server where
           there is one.
      iv. The python packages are installed from the default pip index. During
          the installation pip will do a git clone and build from it for any
          packages that have a git SHA as a constraint.
      v. If there are any ``venv_packages_to_symlink`` then the appropriate
         python libraries installed into the system from those packages will be
         symlinked into the virtualenv. This provides for python libraries which
         have a tight coupling with C bindings which may not be portable as a
         wheel.

4. If any ``venv_facts_when_changed`` are set, then they are implemented on
   the target host in ``/etc/ansible/facts.d``.

Default variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

References
~~~~~~~~~~

Documentation for the project can be found at:
  https://docs.openstack.org/ansible-role-python_venv_build/latest/

The project home is at:
  https://launchpad.net/openstack-ansible

Release notes for the project can be found at:
  https://docs.openstack.org/releasenotes/ansible-role-python_venv_build/

The project source code repository is located at:
  https://git.openstack.org/cgit/openstack/ansible-role-python_venv_build

The bug tracker can be found at:
  https://bugs.launchpad.net/openstack-ansible
