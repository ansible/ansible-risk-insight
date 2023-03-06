This sample shows how to call ARI from your code. 

```
example
├── playbooks
│   └── sample_playbook.yml # sample playbook file
├── readme.md   #this document
├── rules
│   └── sample_rule.py  # sample rule
├── sample.py   # sample code
```

For the preparation, see the document in ARI repositogy. Here is the short path for minimal preparation.

```
git clone git@github.com:ansible/ansible-risk-insight.git
cd ansible-risk-insight

# install ARI
pip install -e .

# list of collection crawled for Knowledge Base (KB)
cat << EOS > /tmp/ram_input_list.txt
collection amazon.aws
collection azure.azcollection
collection google.cloud
collection arista.eos
collection junipernetworks.junos
collection containers.podman
collection ansible.builtin
collection community.general
collection ansible.posix
collection arista.avd
EOS

# prepare ARI KB (created under /tmp/ari-data)
ari ram generate -f /tmp/ram_input_list.txt
```

You can run the sample by

```
python example/sample.py
```

See the document [here](../docs/customize_rules.md) to add your own custom rules. 
