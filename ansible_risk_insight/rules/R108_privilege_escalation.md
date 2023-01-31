## privilege escalation
The `privilege escalation` rule identifies a task execution with root privileges or with another user’s permissions.

### Problematic code

```
- name: Run command if /path/to/database does not exist (without 'args')
  ansible.builtin.command: /usr/bin/make_database.sh db_user db_name creates=/path/to/database
  become: true
```
### Correct code

```
- name: Run command if /path/to/database does not exist (without 'args')
  ansible.builtin.command: /usr/bin/make_database.sh db_user db_name creates=/path/to/database
```