=========================
OpenStack-Ansible plugins
=========================

.. toctree::
   :maxdepth: 2

   actions.rst
   filters.rst

Example ansible.cfg file
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/example.ini
   :language: yaml


Example role requirement overload for automatic plugin download
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The Ansible role requirement file can be used to overload the
``ansible-galaxy`` command to automatically fetch the plugins for
you in a given project. To do this add the following lines to your
``ansible-role-requirements.yml`` file.

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml
