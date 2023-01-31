## key config change
The `key config change` rule identifies parameterized key change.

### Problematic code

```
- name: Import a key from a url
  ansible.builtin.rpm_key:
    state: present
    key: http://{{ key_server }}/RPM-GPG-KEY.dag.txt

```
### Correct code

```
- name: Import a key from a url
  ansible.builtin.rpm_key:
    state: present
    key: http://apt.sw.be/RPM-GPG-KEY.dag.txt
```