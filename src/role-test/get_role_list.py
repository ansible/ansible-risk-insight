from ansible.cli.galaxy import GalaxyCLI
import os
import requests

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
        for item in galaxy_roles["content"]["results"]:
            ns = item["summary_fields"]["namespace"]["name"]
            name = item["name"]
            role = "{0}.{1}".format(ns, name)
            print(role)
            roles.append(role)
        print(roles)
        _roles = "\n".join(roles)
        with open("galaxy_roles.txt", "a") as file:
            file.write(_roles)
        if len(galaxy_roles["content"]["results"]) == 0:
            finish = True
    return roles



if __name__ == "__main__":
    list_role()