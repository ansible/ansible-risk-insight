==============================================
Configuring the Key Manager (barbican) service
==============================================

First of all we need to set env.d parameters and define hosts where we want to
run barbican-api. For that we can either extend `openstack_user_config.yml` or
add file `/etc/openstack_deploy/conf.d/barbican.yml` with the following
content:

 .. code-block:: yaml

  key-manager_hosts:
    infra1:
      ip: 172.29.236.11
    infra2:
      ip: 172.29.236.12
    infra3:
      ip: 172.29.236.13

Barbican can be configured to work in both single and multibackend modes. It
depends on the number of keys in ``barbican_backends_config`` dictionary. Also
you must explicitly define default backend in case variable contains
configuration for more then one backend, for example:

 .. code-block:: yaml

    barbican_backends_config:
      software:
        secret_store_plugin: store_crypto
        crypto_plugin: simple_crypto
      hsm:
        secret_store_plugin: store_crypto
        crypto_plugin: p11_crypto
        global_default: True

In addition to that you need to define plugin specific config, which can be
done with definition of the variable ``barbican_plugins_config``. Each key
of this dictionary will be used to as config section name and values should
be considered as key-value config options, like config_overrides options.

 .. code-block:: yaml

  barbican_plugins_config:
    simple_crypto_plugin:
      kek: "{{ barbican_simple_crypto_key | b64encode }}"

Once all variables are set and configuration is done, you can deploy
Barbican by running following playbooks:

 .. code::

  # openstack-ansible playbooks/lxc-containers-create.yml --limit lxc_hosts,barbican_all
  # openstack-ansible playbooks/os-barbican-install.yml
  # openstack-ansible playbooks/haproxy-install.yml


Configuring Barbican with Thales Luna HSM backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As example we will show configuration for Thales Luna Network HSM (Safenet).
Barbican stores in HSM only HMAC and MKEK keys, that are used to encrypt and
decrypt keys that are stored in Barbican MySQL database.

MKEK is Master Key Encryption Key, which is used to encrypt KEKs that are
unique and created per project. All keys within a project are encrypted with
KEK.

You need to create a Data Protection On Demand sevice and complete an
initialization of the Luna slot. You can follow `lunacm documentation <https://thalesdocs.com/gphsm/luna/6.3/docs/network/Content/configuration/ppso_partition_config/partition-so_action_to_config_pw-ppso_partition_2.htm>`_
for more details. As a result of setup you should have:

#. Crypto Officer role password
#. Generated Chrystoki.conf
#. Binaries of libdpod.plugin and libCryptoki2.so

.. note::

  At the moment barbican does not support Thales FIPS mode. Also mention, that
  Crypto Officer role password has to be reset on the first login, which should
  be done right after initialization of the CO role.

Once setup of the Thales is done, we can define all required variables that are
needed for the Barbican deployment. Define in `user_variables.yml` following:

 .. code-block:: yaml

  barbican_backends_config:
    hsm:
      secret_store_plugin: store_crypto
      crypto_plugin: p11_crypto

  barbican_plugins_config:
    p11_crypto_plugin:
      library_path: /opt/barbican/libs/libCryptoki2.so
      login: "{{ barbican_dpod_co_password }}"
      slot_id: 3
      mkek_label: thales_mkek_3
      mkek_length: 32
      hmac_label: thales_hmac_3

  barbican_user_libraries:
    - src: /etc/openstack_deploy/barbican/libCryptoki2.so
      dest: /opt/barbican/libs/libCryptoki2.so
    - src: /etc/openstack_deploy/barbican/libdpod.plugin
      dest: /opt/barbican/libs/plugins/libdpod.plugin
    - src: /etc/openstack_deploy/barbican/Chrystoki.conf
      dest: /opt/barbican/Chrystoki.conf

You should also add ``barbican_dpod_co_password`` to `user_secrets.yml`
and set to the value of Crypto Officer role password.

We would need to symlink Chrystoki.conf so /etc. Additionally it is required
to manually generate hmac and mkek keys, that would be stored on HSM.

 .. code::

  # ansible -m file -a "src=/opt/barbican/Chrystoki.conf dest=/etc/Chrystoki.conf state=link" barbican_all
  # ansible -m command -a "/openstack/venvs/barbican-{{ venv_tag }}/bin/barbican-manage hsm gen_hmac --library-path /opt/libs/64/libCryptoki2.so --passphrase {{ barbican_dpod_co_password }} --slot-id 3 --label thales_hmac_3" barbican_all[0]
  # ansible -m command -a "/openstack/venvs/barbican-{{ venv_tag }}/bin/barbican-manage hsm gen_mkek --library-path /opt/libs/64/libCryptoki2.so --passphrase {{ barbican_dpod_co_password }} --slot-id 3 --label thales_mkek_3" barbican_all[0]


Configuring Barbican with Vault backend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

HashiCorp Vault is pretty popular key storage engine that is used in production
by a lot of companies.
You have 2 ways to use Vault with OpenStack:

#. Connect services directly to Vault with Castellan.
   In this case all keys would be stored inside Vault under the same user and
   no tenant isolation will be present.
   This option does not require Barbican deployment at all.
#. Connect services to Barbican, Barbican is connected to Vault.
   In this scenario we configure Castellan to use Barbican driver and services
   will reach it for the secrets. In this case Barbican will generate KEK which
   will be unique per project and store secrets inside it's MySQL database.
   Master KEKs in their turn will be stored inside Vault.

In both options you would need to create a KV2 Secret Storage in Vault.

Connect services directly to Vault
----------------------------------

Eventually this section is not related to Barbican at all, since it does not
require Barbican endpoints to be present at all and it needs only services
configuration (like Nova or Cinder). To use it you would need to define
following overrides is `user_variables.yml`:

 .. code-block:: yaml

    nova_nova_conf_overrides:
      key_manager:
        backend: vault
      vault:
        kv_mountpoint: secret
        root_token_id: "{{ vault_root_token }}"
        vault_url: https://vault.example.com
        use_ssl: True

    cinder_cinder_conf_overrides:
      key_manager:
        backend: vault
      vault:
        kv_mountpoint: secret
        root_token_id: "{{ vault_root_token }}"
        vault_url: https://vault.example.com
        use_ssl: True

After variables are set we need to run roles to re-configure services:

 .. code::

   # openstack-ansible playbooks/os-cinder-install.yml --tags cinder-config
   # openstack-ansible playbooks/os-nova-install.yml -- tags nova-config


Connect Barbican to Vault
-------------------------

You need to define variables like shown in the sample below to configure
Babrican to use Vault store driver:

 .. code-block:: yaml

    barbican_backends_config:
      vault:
        secret_store_plugin: vault_plugin
        crypto_plugin: simple_crypto

    barbican_plugins_config:
      vault_plugin:
        kv_mountpoint: secret
        root_token_id: "{{ vault_root_token }}"
        vault_url: https://vault.example.com
        use_ssl: True


Configuring services to work with Barbican
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

We need to let know Cinder, Nova and other services that key storage (Barbican)
is available now for interaction. There are special variables like
``<service>_barbican_enabled`` that should be set to True once there are at
least one host in ``barbican_all`` group. So generally it should be enough
just to re-run service-related roles to get service's config adjusted to
interact with barbican:

.. code::

  # openstack-ansible playbooks/os-cinder-install.yml --tags cinder-config
  # openstack-ansible playbooks/os-nova-install.yml --tags nova-config

Then we can make use of barbican, for example, to make LUKS-encrypted volumes.
You may reference to `Cinder docs <https://docs.openstack.org/cinder/latest/configuration/block-storage/volume-encryption.html#create-an-encrypted-volume-type>`_
for sample usage.

You should also make sure, that tenants do have `creator` role assigned
as it is required to be able to create secrets in Barbican.
