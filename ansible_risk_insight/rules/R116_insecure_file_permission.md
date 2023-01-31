## insecure file permission
The `insecure file permission` rule checks whether a task gives insecure permissions to a file.

### Problematic code

```
- name: Change file permissions
  ansible.builtin.file:
    path: /work
    owner: root
    group: root
    mode: '1777'
```
### Correct code

```
- name: Change file permissions
  ansible.builtin.file:
    path: /work
    owner: root
    group: root
    mode: '0755'
```