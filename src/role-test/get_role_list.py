from ansible.cli.galaxy import GalaxyCLI
import os
import requests
import json

# def collection_install_requirements(self, requirements, collection_dir):
#     # requirements.yml
#     # r_file = os.path.join(self._project_dir, 'requirements.yml')
#     print("installing ", requirements)
#     if os.path.exists(requirements):
#         galaxy_args = ['ansible-galaxy', 'collection', 'install', '-r', requirements,
#             '-p', collection_dir]
#         gcli = GalaxyCLI(args=galaxy_args)
#         gcli.run()
#     return

# def role_install(name, tmp_dir):
#     # ansible-galaxy install geerlingguy.java
#     print("install role", name)
#     galaxy_args = ['ansible-galaxy', 'install', name,
#     '-p', tmp_dir]
#     gcli = GalaxyCLI(args=galaxy_args)
#     gcli.run()
#     return

# def collection_install(collection, collection_dir):
#     print("install collection", collection)
#     galaxy_args = ['ansible-galaxy', 'collection', 'install', collection,
#     '-p', collection_dir]
#     gcli = GalaxyCLI(args=galaxy_args)
#     gcli.run()
#     return

def list_role():
    finish = False
    count = 0
    while finish is not True:
        roles = []
        count += 1
        # api_url = "https://galaxy.ansible.com/api/internal/ui/search/?type=role"
        api_url =  "https://galaxy.ansible.com/api/internal/ui/search/?format=json&type=role&page=NUM"
        api_url = api_url.replace("NUM", str(count))
        response = requests.get(api_url)
        galaxy_roles = response.json()
        # for item in galaxy_roles["content"]["results"]:
        #     ns = item["summary_fields"]["namespace"]["name"]
        #     role = "{0}.{1}".format(ns, item["name"])
        #     print(role)
        #     roles.append(role)
        # print(roles)
        # _roles = "\n".join(roles)
        # with open("galaxy_roles.txt", "a") as file:
        #     file.write(_roles)
        for item in galaxy_roles["content"]["results"]:
            with open("galaxy_role_dump.json", "a") as file:
                json.dump(item, file)
                file.write("\n")
        if len(galaxy_roles["content"]["results"]) == 0:
            finish = True
    return roles

def gen_compact_dict():
    roles = []
    with open("galaxy_role_dump.json", "r") as file:
        lines = file.readlines()
    for line in lines:
        item = json.loads(line)
        ns = item["summary_fields"]["namespace"]["name"]
        role_name = "{0}.{1}".format(ns, item["name"])
        role = {"ns": ns, "name": role_name, "download_count": item["download_count"], "search_rank": item["search_rank"], "download_rank": item["download_rank"] }            
        roles.append(role)
    sorted_roles = sorted(roles, key=lambda x: x['download_count'], reverse=True)
    for sr in sorted_roles:
        with open("galaxy_roles2.txt", "a") as file:
            json.dump(sr, file)
            file.write("\n")

if __name__ == "__main__":
    # list_role()
    gen_compact_dict()