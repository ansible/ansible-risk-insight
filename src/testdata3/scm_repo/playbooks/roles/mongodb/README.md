Ansible role to prepare MongoDB installation
============================================

This role prepares the installation of MongoDB using the greendayonfire.mongodb
role on an OpenStack server.  It mounts a volume on /var/lib/mongodb and
contains scripts to support tarsnap backups.

Role Variables
--------------

``MONGODB_OPENSTACK_DB_DEVICE`` --- the volume to mount, e.g. ``/dev/vdb1``
``MONGODB_SERVER_BACKUP_DIR`` --- the directory files for backup are prepared in.
