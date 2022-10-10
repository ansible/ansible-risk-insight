# Ansible Risk Insight

![ari arch](doc/images/ari-arch.png)


## Installation (for development)

In a virtual environment:

```
git clone git@github.com:rurikudo/ansible-risk-insight.git
cd ansible-risk-insight
pip install -e .
```

## How to try

### Role
```
ansible-risk-insight role <role_name>
```

### Collection (now fixing an issue)
```
ansible-risk-insight collection <collection_name>
```

All intermediate files are installed under a temporary directory.
The src dir which includes dependency collections and roles are moved under command dir for ARI to avoid repeated install from Galaxy repository.
The location of the ARI common dir can be specified by env variable `ARI_DATA_DIR` (default = /tmp/ari-data)

## Extensibility

### Custom Annotator

An Annotator implements a logic to derive finding from each individual task object. It implements [Annotator](src/annotators/base.py#L1-L9) class. Annotators are under [/ansible_risk_insight/annotators](ansible_risk_insight/annotators/) directory.
- [ansible_builtin.py](ansible_risk_insight/annotators/ansible_builtin.py) : annotator for ansible.builtin modules
- [sample_custom_annotator.py](ansible_risk_insight/annotators/sample_custom_annotator.py) : sample annotator for other modules

### Custom Rule
A Rule implements a logic to derive findings composed of multiple findings from a series of tasks. It implements [Rule](ansible_risk_insight/annotators/base.py#L1-L9) class. Rules are under [/ansible_risk_insight/rules](ansible_risk_insight/rules/) directory.


