## parameterized package install
The `parameterized package install` rule identifies parameterized package installation.

### Problematic code

```
- name: Install the nginx rpm from a remote repo
  ansible.builtin.yum:
    name: {{ nginx_rpm_url }}
    state: present
```
### Correct code

```
- name: Install the nginx rpm from a remote repo
  ansible.builtin.yum:
    name: http://nginx.org/packages/centos/6/noarch/RPMS/nginx-release-centos-6-0.el6.ngx.noarch.rpm
    state: present
```