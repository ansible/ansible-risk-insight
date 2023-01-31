##  pkg install with insecure option
The `pkg install with insecure option` rule identifies an pkg installation with insecure option.

### Problematic code

```
- name: Install the nginx rpm from a remote repo
  ansible.builtin.yum:
    name: http://nginx.org/packages/centos/6/noarch/RPMS/nginx-release-centos-6-0.el6.ngx.noarch.rpm
    state: present
    validate_certs: false
```
### Correct code

```
- name: Install the nginx rpm from a remote repo
  ansible.builtin.yum:
    name: http://nginx.org/packages/centos/6/noarch/RPMS/nginx-release-centos-6-0.el6.ngx.noarch.rpm
    state: present
```