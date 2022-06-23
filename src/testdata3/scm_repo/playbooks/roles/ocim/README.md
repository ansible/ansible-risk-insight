Ansible role for the deployment of the OpenCraft Instance Manager
=================================================================

The role in this directory can be used to deploy the OpenCraft Instance Manager to a server
running on Ubuntu 16.04 xenial.  It has been tested with this image:

https://cloud-images.ubuntu.com/xenial/current/xenial-server-cloudimg-amd64-disk1.img

You need to point the DNS to the web server itself.  If using websockets, there would be another subdomain
for web sockets (e.g. websockets.ocimdomain.com), but websockets have been disabled as of now.

The databases need to run on external servers.  The server deployed by this role is intended to
be stateless, and no backups are performed by default.

Prepare configuration file
--------------------------

Create a file `private.yml` with your settings for the instance manager.  Most of the settings go in the
`OPENCRAFT_ENV_TOKENS` dictionary, e.g.

    OPENCRAFT_ENV_TOKENS:
      DATABASE_URL: 'postgres://db-user:password@postgres.example.com:port/db-name'
      DEFAULT_FORK: 'edx/edx-platform'
      SECRET_KEY: 'your-secret-key-goes-here'

Set `OPENCRAFT_OPENSTACK_SSH_KEY_FILE` to the name of the private SSH key to be used to access
OpenStack servers.  You must upload the corresponding public key to the OpenStack project
configured in OPENCRAFT_ENV_TOKENS and set OPENSTACK_SANDBOX_SSH_KEYNAME to the name of the key.

See the [`README.md`][1] file and [`opencraft/settings.py`][2] for further details on settings you
want to include there.

[1]: https://github.com/open-craft/opencraft/blob/master/README.md
[2]: https://github.com/open-craft/opencraft/blob/master/opencraft/settings.py

### Deployment of swift backup

Optionally Instance Manager allows you to set up SWIFT container for spawned edx instances (bear in mind that
support for swift containers hasn't been merged to master by the time of writing that). More optionally yet
this swift containers may be backed up to tarsnap service.  To do this you'll need to set all variables starting
from: `OPENCRAFT_BACKUP_SWIFT_*`.

Swift backup downloads all swift containers, to local drive (this is the only way to back them up to Tarsnap), these
containers might take a lot of space --- so it might be good idea to mount download them to a separate filesystem.

To do this you'll need to:

1. Create a OpenStack Volume.
2. Partition it (create a single partition --- use `fdisk`)
3. Create ext4 filesystem on it `mkfs.ext4 -j`.
4. Set `OPENCRAFT_BACKUP_SWIFT_MOUNT_DEVICE` to point to this device.

Run the playbook
----------------

1. Install Ansible, e.g. by creating a new virtualenv and running

        pip install -r requirements.txt

2. Prepare your server with a stock Ubuntu 16.04 image, and make sure you can SSH to it.

3. Run the playbook:

        ansible-playbook playbooks/ocim.yml --extra-vars @private.yml -i your.host.name.here,

   (The trailing comma must be preserved.). Note: you can't pass naked ip address to -i switch, long
   story short this will make `forward-server-mail` explode when configuring postfix. Please temporarily
   add hostname mapping to your hosts if you need to, or just create an ansible ``hosts`` file.

After deployment, the server runs inside a screen session.  To restart it or to see the console
output, you need to log in and attach to the screen session using `screen -r`.  To detach again use
the keyboard shortcut `C-a d`.

Show changes that would be applied to `.env` file
-------------------------------------------------

To see the difference between the current `.env` file on the server and the
version that will be created by the ansible playbook, you can use this command
line:

    ansible-playbook  playbooks/ocim.yml \
        --check --diff -t ocim-env-file
        -u ubuntu --extra-vars @private.yml -i your.host.name.here,

It will start a dry-run of Ansible in diff mode, and only run the task to update
the env file.
