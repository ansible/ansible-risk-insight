================================
Swift role for OpenStack-Ansible
================================

.. toctree::
   :maxdepth: 2

   configure-swift.rst

Default Variables
~~~~~~~~~~~~~~~~~

.. literalinclude:: ../../defaults/main.yml
   :language: yaml
   :start-after: under the License.

Example Playbook
~~~~~~~~~~~~~~~~

.. literalinclude:: ../../examples/playbook.yml
   :language: yaml

Dependencies
~~~~~~~~~~~~

This role needs pip >= 7.1 installed on the target host.

Tags
~~~~

This role supports two tags: ``swift-install`` and ``swift-config``.

The ``swift-install`` tag can be used to install the software.

The ``swift-config`` tag can be used to maintain configuration of the
service, and do runtime operations.
