## unauthorized download source
The `unauthorized download source` rule checks whether a task download a source from an authorized location. 
Authorized locations can be defined using the allow url list and deny url list.

### Problematic code

```
# allow_url_list = ["https://valid*", "https://myurl*"]

- name: Download sample app installation script.
  get_url:
    url: https://invalid.example.com/path/install_script.sh
    dest: /tmp/install_script.sh
```
### Correct code

```
# allow_url_list = ["https://valid*", "https://myurl*"]

- name: Download sample app installation script.
  get_url:
    url: https://valid.example.com/path/install_script.sh
    dest: /tmp/install_script.sh
```