## outbound data transfer
The `outbound data transfer` rule identifies that an outbound data transfer from a parameterized source.

### Problematic code

```
- name: POST from contents of remote file
  ansible.builtin.uri:
    url: {{ url }}
    method: POST
    src: /path/to/my/file.json
    remote_src: yes
```
### Correct code

```
- name: POST from contents of remote file
  ansible.builtin.uri:
    url: https://httpbin.org/post
    method: POST
    src: /path/to/my/file.json
    remote_src: yes
```