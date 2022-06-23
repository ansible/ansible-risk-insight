# Tarsnap

- An ansible role for operating tarsnap backups

The role downloads sources for, verifies the gpg-encrypted sha signature, compiles, and installs [Tarsnap].
**Batteries included**: cron job, shell wrapper, and [logrotate] policy.

## Requirements

- [Tarsnap] account
- [Tarsnap] machine key file
  - **important** this role assumes you are responsible for copying this key to `tarsnap_keyfile`.

## Variables

Some of the available variables along with default values are listed below:

    tarsnap_version: 1.0.35
    tarsnap_keyfile: "/root/tarsnap.key"
    tarsnap_cache: "/usr/local/tarsnap-cache"

For a complete list, see `defaults/main.yml`.

## Configure Tarsnap

The `tarsnap` role performs some additional steps to configure Tarsnap:

* Creates tarsnap cache directory
* Uploads tarsnap key

## License

Source Copyright © 2014 Paul Bauer. Distributed under the GNU General Public License v3, the same as Ansible uses. See the file COPYING.

[logrotate]:http://linuxcommand.org/man_pages/logrotate8.html
[Tarsnap]:https://www.tarsnap.com/
