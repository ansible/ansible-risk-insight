import json
from keyutil import get_obj_info_by_key


if __name__ == "__main__":
    keys = [
        "task role:geerlingguy.gitlab#taskfile:tasks/main.yml#task:[0]",
        "taskfile role:geerlingguy.gitlab#taskfile:tasks/main.yml",
        "role role:geerlingguy.gitlab",
        "play collection:debops.debops#playbook:playbooks/virt/dnsmasq-persistent_paths.yml#play:[0]",
        "playbook"
        " collection:debops.debops#playbook:playbooks/sys/cryptsetup-plain.yml",
        "module collection:debops.debops#module:debops.debops.apache2_module",
    ]
    for k in keys:
        info = get_obj_info_by_key(k)
        print(json.dumps(info, indent=2))
