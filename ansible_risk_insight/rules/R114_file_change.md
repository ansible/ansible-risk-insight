## file change
The `file change` rule identifies parameterized file change.

### Problematic code

```
- name: Update sshd configuration
  ansible.builtin.template:
    src: {{ sshd_config }} # <-- This parameter can be overwritten.
    dest: /etc/ssh/sshd_config
```
### Correct code

```
- name: Update sshd configuration
  ansible.builtin.template:
    src: etc/ssh/sshd_config.j2
    dest: /etc/ssh/sshd_config
```