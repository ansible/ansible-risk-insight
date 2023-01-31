## command instead of shell
The `command instead of shell` rule checks whether a task uses `shell` module instead of `command` module.
If you want to run a command predictably and securely, it is recommended to use the command module instead of the shell. 

### Problematic code

```
- name: Cat /etc/foo.conf
  ansible.builtin.shell: cat /etc/foo.conf
```

### Correct code
```
- name: Cat /etc/foo.conf
  ansible.builtin.command: cat /etc/foo.conf
```