from ansible.cli.galaxy import GalaxyCLI
import os
import requests
import json

def list_collection():
    finish = False
    count = 0
    while finish is not True:
        roles = []
        count += 1
        # api_url = "https://galaxy.ansible.com/api/internal/ui/search/?type=role"
        api_url =  "https://galaxy.ansible.com/api/internal/ui/search/?format=json&type=collection&page=NUM"
        api_url = api_url.replace("NUM", str(count))
        response = requests.get(api_url)
        galaxy_collections = response.json()
        # for item in galaxy_roles["content"]["results"]:
        #     ns = item["summary_fields"]["namespace"]["name"]
        #     role = "{0}.{1}".format(ns, item["name"])
        #     print(role)
        #     roles.append(role)
        # print(roles)
        # _roles = "\n".join(roles)
        # with open("galaxy_roles.txt", "a") as file:
        #     file.write(_roles)
        print(galaxy_collections)
        for item in galaxy_collections["collection"]["results"]:
            with open("galaxy_collection_dump.json", "a") as file:
                json.dump(item, file)
                file.write("\n")
        if len(galaxy_collections["collection"]["results"]) == 0:
            finish = True
    return roles

def gen_compact_dict():
    roles = []
    with open("galaxy_collection_dump.json", "r") as file:
        lines = file.readlines()
    for line in lines:
        item = json.loads(line)
        ns = item["namespace"]["name"]
        name =item["name"]
        fqcn = "{0}.{1}".format(ns, name)
        role = {"ns": ns, "name": name, "fqcn": fqcn ,"download_count": item["download_count"]}            
        roles.append(role)
    sorted_roles = sorted(roles, key=lambda x: x['download_count'], reverse=True)
    for sr in sorted_roles:
        with open("galaxy_collections.txt", "a") as file:
            json.dump(sr, file)
            file.write("\n")

if __name__ == "__main__":
    # list_collection()
    gen_compact_dict()