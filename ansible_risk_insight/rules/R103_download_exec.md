## download exec
The `download exec` rule checks whether a task executes downloaded file from parameterized source.

### Problematic code

```
- name: Download sample app installation script.
  get_url:
    url: "{{ app_installation_script_url }}"  # <-- This parameter can be overwritten.
    dest: /tmp/install_script.sh

- name: Install sample app.
  command: bash /tmp/install_script.sh
```
### Correct code

```
- name: Download sample app installation script.
  get_url:
    url: https://example.com/path/install_script.sh
    dest: /tmp/install_script.sh

- name: Install sample app.
  command: bash /tmp/install_script.sh
```