## file deletion
The `file deletion` rule identifies parameterized file deletion. 
If state option is absent, directories will be recursively deleted, and files or symlinks will be unlinked.

### Problematic code

```
- name: Recursively remove directory
  ansible.builtin.file:
    path: {{ path_to_dir }} # <-- This parameter can be overwritten.
    state: absent

```
### Correct code

```
- name: Recursively remove directory
  ansible.builtin.file:
    path: /etc/foo
    state: absent
```