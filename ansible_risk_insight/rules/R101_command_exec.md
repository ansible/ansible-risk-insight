## command exec
The `command exec` rule checks whether a task executes parameterized command.

### Problematic code

```
- name: Run command.
  command: bash {{ install_script }} # <-- This parameter can be overwritten.
```
### Correct code

```
- name: Run command.
  command: bash /tmp/install_script.sh
```