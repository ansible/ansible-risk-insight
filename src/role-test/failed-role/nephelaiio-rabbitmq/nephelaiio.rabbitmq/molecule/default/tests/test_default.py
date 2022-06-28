import os

import testinfra.utils.ansible_runner

testinfra_hosts = testinfra.utils.ansible_runner.AnsibleRunner(
    os.environ['MOLECULE_INVENTORY_FILE']).get_hosts('all')


def test_rabbitmq(host):
    service_name = 'rabbitmq-server'
    if host.system_info.distribution in ['arch']:
        service_name = 'rabbitmq'
    assert host.service(service_name).is_enabled
    assert host.service(service_name).is_running
    assert host.command('rabbitmqctl help').rc == 0
