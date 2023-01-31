## non fqcn use
The `non fqcn use` rule checks whether a task uses a short name module.

### Problematic code

```
- name: Install collection community.network
  ansible_galaxy_install:
    type: collection
    name: community.network
```

### Correct code

```
- name: Install collection community.network
  community.general.ansible_galaxy_install:
    type: collection
    name: community.network
```