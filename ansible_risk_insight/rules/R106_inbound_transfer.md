## inbound data transfer
The `inbound data transfer` rule identifies that an inbound data transfer from a parameterized source.

### Problematic code

```
- name: Download file 
  ansible.builtin.get_url:
    url: https://{{ example_url }}/path/file.conf # <-- This parameter can be overwritten.
    dest: /etc/file.conf
```
### Correct code

```
- name: Download file 
  ansible.builtin.get_url:
    url: https://example.com/path/file.conf
    dest: /etc/file.conf
```