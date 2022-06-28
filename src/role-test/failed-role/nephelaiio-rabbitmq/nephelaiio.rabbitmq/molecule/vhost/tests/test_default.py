import os
import re

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_rabbitmq(host):
    vhost_out = host.check_output(
        'rabbitmqctl list_vhosts')
    assert re.match('^molecule_vhost$',
                    vhost_out.split('\n')[1])
    user_out = host.check_output(
        'rabbitmqctl list_users')
    assert re.match('molecule_user\s+\[\]$',
                    user_out.split('\n')[1])
    perms_out = host.check_output(
        'rabbitmqctl list_user_permissions molecule_user')
    assert re.match('^molecule_vhost\s+conf\s+write\s+read$',
                    perms_out.split('\n')[1])
