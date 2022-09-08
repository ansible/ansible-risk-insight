# Ansible Risk Insight 

![ari arch](https://github.com/rurikudo/ansible-risk-insight/blob/main/doc/images/ari-arch.png)


## Installation
```
git clone git@github.com:rurikudo/ansible-risk-insight.git
cd ansible-risk-insight/src
pip install -r requirements.txt
```

## How to try

### Role
```
python ansible_risk_insight.py role <role_name>
```

### Collection (now fixing an issue)
```
python ansible_risk_insight.py collection <collection_name>
```

All intermediate files are installed under a temporary directory. 
The src dir which includes dependency collections and roles are moved under command dir for ARI to avoid repeated install from Galaxy repository.
The location of the ARI common dir can be specified by env variable `ARI_DATA_DIR` (default = <home_dir>/.ari)

## Extensibility

### Custom Extractor

An Extractor implements a logic to derive finding from each individual task object. It implements [Extractor](src/extractors/base.py#L1-L9) class. Extractors are under /extractors directory. 
- [ansible_builtin.py](src/extractors/ansible_builtin.py) : extractor for ansible.builtin modules
- [sample_custom_extractor.py]((src/extractors/ansible_builtin.py) : sample extractor for other modules 

### Custom Rule
A Rule implements a logic to derive findings composed of multiple findings from a series of tasks. It implements [Rule](https://github.com/rurikudo/ansible-risk-insight/blob/main/src/extractors/base.py#L1-L9) class. Rules are under /extractors directory. 


