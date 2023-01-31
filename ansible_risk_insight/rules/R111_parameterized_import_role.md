##  parameterized import role
The `parameterized import role` rule checks whether a task imports or includes a parameterized role.

### Problematic code

```
  tasks:
    - ansible.builtin.import_role:
        name: {{ my_role }}

```
### Correct code

```
  tasks:
    - ansible.builtin.import_role:
        name: myrole
```