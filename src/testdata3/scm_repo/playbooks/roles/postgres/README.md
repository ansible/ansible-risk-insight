Ansible role to prepare PostgreSQL installation
===============================================

This role prepares the installation of PostgreSQL using the ANXS.postgresql role
on an OpenStack server.  It mounts a volume on /var/lib/postgresql and contains
scripts to support tarsnap backups.

Role Variables
--------------

``POSTGRES_OPENSTACK_DB_DEVICE`` --- the volume to mount, e.g. ``/dev/vdb1``
``POSTGRES_SERVER_BACKUP_DIR`` --- the directory files for backup are prepared in.
