
##  parameterized import taskfile
The `parameterized import taskfile` rule identifies whether a task imports or includes a parameterized task file.

### Problematic code

```
    - name: Include task list in play
      ansible.builtin.import_tasks:
        file: {{ task_file }} 

```
### Correct code

```
    - name: Include task list in play
      ansible.builtin.import_tasks:
        file: stuff.yaml
```