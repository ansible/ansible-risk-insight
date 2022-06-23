import json

testinfra_hosts = ['vault-host']

def test_vault_deploy(host):
    cmd = host.run(". /home/ubuntu/.vault-env ; vault status --format json")
    print(cmd.stdout)
    print(cmd.stderr)
    assert json.loads(cmd.stdout)['initialized'] is True
    assert cmd.rc == 0
