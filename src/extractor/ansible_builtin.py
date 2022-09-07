
from multiprocessing.spawn import is_forking
from re import T
from unicodedata import category
import json


class BuiltinExtractor():
    def __init__(self):
        self.analyzed_task = {}
        self.analyzed_data = []
    
    def run(self, task):
        self.reset()
        if "resolved_name" not in task:
            return
        if "module_options" not in task:
            return
        resolved_name = task["resolved_name"]
        self.analyzed_task["resolved_name"] = resolved_name
        self.analyzed_task["key"] = task["key"]
        options = task["module_options"]
        resolved_options = task["resolved_module_options"]
        resolved_variables = task["resolved_variables"]

        # builtin modules
        if resolved_name == "ansible.builtin.get_url":
            res = {"category": "inbound_transfer" , "data": {},  "resolved_data": []}
            res["data"] = self.get_url(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.get_url(ro, resolved_variables))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.fetch":
            # res = {"category": "inbound_transfer" , "data": {},  "resolved_data": []}
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.fetch(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.fetch(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.command":
            res = {"category": "cmd_exec" , "data": {},  "resolved_data": []}
            res["data"] = self.command(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.command(ro, resolved_variables))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.apt":
            res = {"category": "package_install" , "data": {},  "resolved_data": []}
            res["data"] = self.apt(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.apt(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.add_host":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.add_host(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.add_host(ro))
            self.analyzed_data.append(res)        

        if resolved_name == "ansible.builtin.apt_key":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.apt_key(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.apt_key(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.apt_repository":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.apt_repository(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.apt_repository(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.assemble":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.assemble(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.assemble(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.assert":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.builtin_assert(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.builtin_assert(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.async_status":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.async_status(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.async_status(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.blockinfile":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.blockinfile(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.blockinfile(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.copy":
            # res = {"category": "outbound_transfer" , "data": {},  "resolved_data": []}
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.copy(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.copy(ro, resolved_variables))
            self.analyzed_data.append(res)     

        if resolved_name == "ansible.builtin.cron":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.cron(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.cron(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.debconf":
            res = {"category": "config_change" , "data": {},  "resolved_data": []}
            res["data"] = self.debconf(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.debconf(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.debug":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.debug(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.debug(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.dnf":
            res = {"category": "package_install" , "data": {},  "resolved_data": []}
            res["data"] = self.dnf(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.dnf(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.dpkg_selections":
            res = {"category": "package_install" , "data": {},  "resolved_data": []}
            res["data"] = self.dpkg_selections(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.dpkg_selections(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.expect":
            res = {"category": "cmd_exec" , "data": {},  "resolved_data": []}
            res["data"] = self.expect(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.expect(ro, resolved_variables))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.fail":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.fail(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.fail(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.file":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.file(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.file(ro, resolved_variables))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.find":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.find(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.find(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.gather_facts":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.gather_facts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.gather_facts(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.getent":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.getent(options)
            res["resolved_data"] = self.getent(resolved_options)
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.git":
            res = {"category": "inbound_transfer" , "data": {},  "resolved_data": []}
            res["data"], res["category"] = self.git(options, resolved_variables)
            for ro in resolved_options:
                rd, c = self.git(ro, resolved_variables)
                res["resolved_data"].append(rd)
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.group":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.group(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.group(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.group_by":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.group_by(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.group_by(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.hostname":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.hostname(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.hostname(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.iptables":
            res = {"category": "network_change" , "data": {},  "resolved_data": []}
            res["data"] = self.iptables(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.iptables(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.known_hosts":
            res = {"category": "network_change" , "data": {},  "resolved_data": []}
            res["data"] = self.known_hosts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.known_hosts(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.lineinfile":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.lineinfile(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.lineinfile(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.meta":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.meta(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.meta(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.package":
            res = {"category": "package_install" , "data": {},  "resolved_data": []}
            res["data"] = self.package(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.package(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.package_facts":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.package_facts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.package_facts(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.pause":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.pause(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.pause(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.ping":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.ping(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.ping(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.pip":
            res = {"category": "package_install" , "data": {},  "resolved_data": []}
            res["data"] = self.pip(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.pip(ro))
            self.analyzed_data.append(res)  

        if resolved_name == "ansible.builtin.raw":
            res = {"category": "cmd_exec" , "data": {},  "resolved_data": []}
            res["data"] = self.raw(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.raw(ro, resolved_variables))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.reboot":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.reboot(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.reboot(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.replace":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.replace(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.replace(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.rpm_key":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.rpm_key(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.rpm_key(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.script":
            res = {"category": "cmd_exec" , "data": {},  "resolved_data": []}
            res["data"] = self.script(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.script(ro, resolved_variables))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.service":
            res = {"category": "system_change" , "data": {},  "resolved_data": []}
            res["data"] = self.service(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.service(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.service_facts":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.service_facts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.service_facts(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.set_fact":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.set_fact(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.set_fact(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.set_stats":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.set_stats(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.set_stats(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.setup":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.setup(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.setup(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.slurp":
            res = {"category": "inbound_transfer" , "data": {},  "resolved_data": []}
            res["data"] = self.slurp(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.slurp(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.stat":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.stat(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.stat(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.subversion":
            res = {"category": "inbound_transfer" , "data": {},  "resolved_data": []}
            res["data"] = self.subversion(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.subversion(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.sysvinit":
            res = {"category": "system_change" , "data": {},  "resolved_data": []}
            res["data"] = self.sysvinit(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.sysvinit(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.systemd":
            res = {"category": "system_change" , "data": {},  "resolved_data": []}
            res["data"] = self.systemd(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.systemd(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.tempfile":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.tempfile(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.tempfile(ro))
            self.analyzed_data.append(res)
            
        if resolved_name == "ansible.builtin.template":
            res = {"category": "file_change" , "data": {},  "resolved_data": []}
            res["data"] = self.template(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.template(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.unarchive":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"], res["category"] = self.unarchive(options, resolved_variables, resolved_options)
            for ro in resolved_options:
                rores, _ = self.unarchive(ro, resolved_variables, resolved_options)
                res["resolved_data"].append(rores)
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.uri":
            res = {"category": "inbound_transfer" , "data": {},  "resolved_data": []}
            res["data"], res["category"] = self.uri(options, resolved_variables)
            for ro in resolved_options:
                rd, c = self.uri(ro, resolved_variables)
                res["resolved_data"].append(rd)
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.user":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.user(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.user(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.validate_argument_spec":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.validate_argument_spec(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.validate_argument_spec(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.wait_for":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.wait_for(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.wait_for(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.wait_for_connection":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.wait_for_connection(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.wait_for_connection(ro))
            res = self.wait_for_connection(task)
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.yum":
            res = {"category": "package_install" , "data": {},  "resolved_data": []}
            res["data"] = self.yum(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.yum(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.yum_repository":
            res = {"category": "" , "data": {},  "resolved_data": []}
            res["data"] = self.yum_repository(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.yum_repository(ro))
            self.analyzed_data.append(res)

        if resolved_name == "ansible.builtin.shell":
            res = {"category": "cmd_exec" , "data": {},  "resolved_data": []}
            res["data"] = self.shell(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.shell(ro, resolved_variables))
            self.analyzed_data.append(res)
        
        if len(self.analyzed_data) != 0:
            # root
            res = self.root(task)
            if res["data"]["root"]:
                self.analyzed_data.append(res)

        self.analyzed_task["analyzed_data"] = self.analyzed_data
        return self.analyzed_task
    
    def reset(self):
        self.analyzed_task = {}
        self.analyzed_data = []

    def root(self, task):
        is_root = False
        if "become" in task["options"] and task["options"]["become"]:
            is_root = True
        res = {"category": "privilege_escalation" , "data": {"root": is_root}}
        return res

    def get_url(self, options, resolved_variables):
        data = {}
        # original options
        if type(options) is not dict:
            return data
        if "url" in options:
            data["src"] =  options["url"]
        if "dest" in options:
            data["dest"] = options["dest"]
        if "mode" in options:
            # todo: check if octal number
            data["mode"] = options["mode"]
        if "checksum" in options:
            data["checksum"] = options["checksum"]
        if "validate_certs" in options:
            if not options["validate_certs"] or options["validate_certs"] == "no":
                data["validate_certs"] = False
        # injection risk
        for rv in resolved_variables:
            if "src" in data and type(data["src"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["src"], rv)
                if undetermined:
                    data["undetermined_src"] = True    
            if "dest" in data and type(data["dest"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["dest"], rv)
                if undetermined:
                    data["undetermined_dest"] = True           
        # unsecure src/dest

        return data

    def fetch(self,options):
        data = {}
        if type(options) is not dict:
            return data
        data["src"] = options["src"]
        data["dest"] =  options["dest"]
        return data

    def command(self,options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] =  options
        else:
            if "cmd" in options:
                data["cmd"] =  options["cmd"]
            if "argv" in options:
                data["cmd"] =  options["argv"]
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["cmd"], rv)
                if undetermined:
                    data["undetermined_cmd"] = True           
        return data

    def apt(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "pkg" in options:
            data["pkg"] = options["pkg"]
        if "name" in options:
            data["pkg"] =  options["name"]
        if "package" in options:
            data["pkg"] = options["package"]
        if "deb" in options:
            data["pkg"] = options["deb"]
        if "allow_unauthenticated" in options and options["allow_unauthenticated"]:
            data["unauthenticated"] = True
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data
    
    def assemble(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "dest" in options:
            data["file"] =  options["dest"]
        if "src" in options:
            data["content"] = options["src"]
        if "mode" in options:
            data["mode"] = options["mode"]            
        return data

    def blockinfile(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] =  options["path"]
        if "dest" in options:
            data["file"] =  options["dest"]
        if "block" in options:
            data["content"] = options["block"]
        if "mode" in options:
            data["mode"] = options["mode"]
        if "unsafe_writes" in options and options["unsafe_writes"]:
            data["unsafe_writes"] = True 
        return data
 
    def copy(self, options, resolved_variables):
        data = {}
        if type(options) is not dict:
            return data
        if "dest" in options:
            data["dest"] =  options["dest"]
        if "src" in options:
            data["src"] = options["src"]
        if "content" in options:
            data["src"] = options["content"]
        if "mode" in options:
            data["mode"] = options["mode"]
        for rv in resolved_variables:
            if "dest" in data and type(data["dest"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["dest"], rv)
                if undetermined:
                    data["undetermined_dest"] = True   
            if "src" in data and type(data["src"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["src"], rv)
                if undetermined:
                    data["undetermined_src"] = True   
        return data
    
    def git(self, options, resolved_variables):
        data = {}
        category = "inbound_transfer"
        if type(options) is not dict:
            return data
        if "repo" in options:
            data["src"] =  options["repo"]
        if "dest" in options:
            data["dest"] = options["dest"]
        if "version" in options:
            data["version"] = options["version"]
        if "clone" in options and ( not options["clone"] or options["clone"] == "no"):
            category = ""
            return data, category
        if "update" in options and ( not options["update"] or options["update"] == "no"):
            category = ""
            return data, category
        # injection risk
        for rv in resolved_variables:
            if "src" in data and type(data["src"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["src"], rv)
                if undetermined:
                    data["undetermined_src"] = True   
            if "dest" in data and type(data["dest"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["dest"], rv)
                if undetermined:
                    data["undetermined_dest"] = True   
        return data,category
    
    def iptables(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "chain" in options:
            data["chain"] = options["chain"]
        if "jump" in options:
            data["rule"] = options["jump"]
        if "policy" in options:
            data["rule"] = options["policy"]
        if "protocol" in options:
            data["protocol"] = options["protocol"]
        return data
    
    def known_hosts(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] = options["path"]            
        if "name" in options:
            data["name"] = options["name"]
        if "key" in options:
            data["key"] = options["key"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True  
        return data
    
    def lineinfile(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "dest" in options:
            data["file"] =  options["dest"]
        if "path" in options:
            data["file"] =  options["path"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        # if "regexp" in options:
        #     self.analyzed_data["file_change"][""] = options["regexp"]
        if "line" in options:
            data["content"] = options["line"]
        if "mode" in options:
            data["mode"] = options["mode"]   
        return data
    
    def package(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data
    
    def pip(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data

    def raw(self,options, resolved_variables):
        data = {}
        if type(options) is str:
            data["cmd"] =  options
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["cmd"], rv)
                if undetermined:
                    data["undetermined_cmd"] = True   
        return data
    
    def replace(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "replace" in options:
            data["content"] =  options["replace"] # after
        if "regexp" in options:
            data["regexp"] =  options["regexp"] # before
        if "path" in options:
            data["file"] = options["path"]
        if "dest" in options:
            data["file"] = options["dest"]    
        if "mode" in options:
            data["mode"] = options["mode"] 
        if "unsafe_writes" in options and options["unsafe_writes"]:
            data["unsafe_writes"] = True
        return data
    
    def rpm_key(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "key" in options:
            data["file"] = options["key"]  
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data

    def script(self,options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] =  options
        else:
            if "cmd" in options:
                data["cmd"] =  options["cmd"]
        if "cmd" not in data:
            return data
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["cmd"], rv)
                if undetermined:
                    data["undetermined_cmd"] = True     
        return data
    
    # proxy for multiple more specific service manager modules
    def service(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["name"] = options["name"]  
        if "state" in options:
            data["state"] = options["state"]
        if "enabled" in options:
            data["enabled"] = options["enabled"] 
            if options["enabled"] == "yes":
                data["enabled"] = True
            if not options["enabled"] == "no":
                data["enabled"] = False
        return data
    
    def sysvinit(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["name"] = options["name"]  
        if "state" in options:
            data["state"] = options["state"]
        if "enabled" in options:
            data["enabled"] = options["enabled"] 
            if options["enabled"] == "yes":
                data["enabled"] = True
            if not options["enabled"] == "no":
                data["enabled"] = False
        return data

    def shell(self,options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] =  options
        else:
            if "cmd" in options:
                data["cmd"] =  options["cmd"]
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["cmd"], rv)
                if undetermined:
                    data["undetermined_cmd"] = True   
        return data

    def slurp(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "src" in options:
            data["src"] = options["src"]
        if "path" in options:
            data["src"] = options["path"]
        return data

    def subversion(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "repo" in options:
            data["src"] =  options["repo"]
        if "dest" in options:
            data["dest"] = options["dest"]
        return data

    def systemd(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["name"] = options["name"]  
        if "state" in options:
            data["state"] = options["state"]
        if "enabled" in options:
            data["enabled"] = options["enabled"] 
            if options["enabled"] == "yes":
                data["enabled"] = True
            if not options["enabled"] == "no":
                data["enabled"] = False
        return data
    
    def tempfile(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] =  options["path"]
        if "prefix" in options:
            data["file"] =  options["prefix"]
        if "suffix" in options:
            data["file"] = options["suffix"]
        return data
    
    def template(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "src" in options:
            data["content"] =  options["src"]
        if "dest" in options:
            data["file"] =  options["dest"]
        if "mode" in options:
            data["mode"] = options["mode"]
        if "group" in options:
            data["group"] = options["group"]
        if "owner" in options:
            data["owner"] = options["owner"]
        if "unsafe_writes" in options and options["unsafe_writes"]:
            data["unsafe_writes"] = True 
        return data

    def uri(self,options, resolved_variables):
        category = ""
        data = {}
        if type(options) is not dict:
            return data, category
        if "method" in options and (options["method"] == "POST" or options["method"] == "PUT" or options["method" == "PATCH"]):
            category = "outbound_transfer"
            if "url" in options:
                data["dest"] =  options["url"]
            for rv in resolved_variables:
                if "dest" in data and type(data["dest"]) is str:
                    data, undetermined = self.resolved_variable_check(data, data["dest"], rv)
                    if undetermined:
                        data["undetermined_dest"] = True   
        elif "method" in options and options["method"] == "GET":
            if "url" in options:
                data["src"] =  options["url"]
            if "dest" in options:
                data["dest"] = options["dest"]
            if "validate_certs" in options:
                data["validate_certs"] = options["validate_certs"]
            if "unsafe_writes" in options:
                data["unsafe_writes"] = options["unsafe_writes"]
            # injection risk
            for rv in resolved_variables:
                if "src" in data and type(data["src"]) is str:
                    if rv["key"] in data["src"] and "{{" in data["src"]:
                        data, undetermined = self.resolved_variable_check(data, data["src"], rv)
                        if undetermined:
                            data["undetermined_src"] = True   
                if "dest" in data and type(data["dest"]) is str:
                    if rv["key"] in data["dest"] and "{{" in data["dest"]:
                        data, undetermined = self.resolved_variable_check(data, data["dest"], rv)
                        if undetermined:
                            data["undetermined_dest"] = True 
        return data, category
    
    def validate_argument_spec(self,options):
        data = {}
        return data
    
    def wait_for(self,options):
        data = {}
        return data

    def wait_for_connection(self,options):
        data = {}
        return data

    def yum(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "list" in options:
            data["pkg"] = options["list"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        if "validate_certs" in options:
            data["validate_certs"] = options["validate_certs"]
        return data

    def yum_repository(self,options):
        data = {}
        return data

    def user(self,options): # config change?
        data = {}
        return data
    
    def unarchive(self, options, resolved_variables, resolved_options):
        category = ""
        data = {}
        if type(options) is not dict:
            return data, category
        if "dest" in options:
            dests = []
            dests.append(options["dest"])
            dests.extend(self.check_nest_variable(options["dest"], resolved_variables))
            # for ro in resolved_options:
            #     if "dest" in ro and ro["dest"] not in dests:
            #         dests.append(ro["dest"])
            data["dest"] = dests 
        if "src" in options:
            src = []
            src.append(options["src"])
            src.extend(self.check_nest_variable(options["src"], resolved_variables))
            # for ro in resolved_options:
            #     if "src" in ro and ro["src"] not in src:
            #         src.append(ro["src"])
            data["src"] = src 
        if "remote_src" in options:  # if yes, don't copy
            data["remote_src"] = options["remote_src"]
        if "unsafe_writes" in options:
            data["unsafe_writes"] = options["unsafe_writes"]    
        if "validate_certs" in options:
            data["validate_certs"] = options["validate_certs"] 
        
        # set category
        # if remote_src=yes and src contains :// => inbound_transfer
        if "remote_src" in data and (data["remote_src"] == "yes" or data["remote_src"]):
            if "src" in data and type(data["src"]) is str and "://" in data["src"]:
                category = "inbound_transfer"
        # check resolved option
        for ro in resolved_options:
            if "remote_src" in ro and (ro["remote_src"] == "yes" or ro["remote_src"]):
                if "src" in ro and type(ro["src"]) is str and "://" in ro["src"]:
                    category = "inbound_transfer"

        for rv in resolved_variables:
            if "dest" in data and type(data["dest"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["dest"], rv)
                if undetermined:
                    data["undetermined_dest"] = undetermined
            elif "dest" in data and type(data["dest"]) is list:
                for d in data["dest"]:
                    data, undetermined = self.resolved_variable_check(data, d, rv)
                    if undetermined:
                        data["undetermined_dest"] = undetermined
            if "src" in data and type(data["src"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["src"], rv)
                if undetermined:
                    data["undetermined_src"] = undetermined
            elif "src" in data and type(data["src"]) is list:
                for d in data["src"]:
                    data, undetermined = self.resolved_variable_check(data, d, rv)
                    if undetermined:
                        data["undetermined_src"] = undetermined
        return data, category

    def cron(self,options):
        data = {}
        return data
    
    def debconf(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "question" in options:
            data["config"] = options["question"]
        return data
    
    def debug(self,options):
        data = {}
        return data
    
    def expect(self,options,resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] =  options
        else:
            if "command" in options:
                data["cmd"] =  options["command"]
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["cmd"], rv)
                if undetermined:
                    data["undetermined_cmd"] = True   
        return data
    
    def dnf(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "list" in options:
            data["pkg"] = options["list"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        if "validate_certs" in options:
            data["validate_certs"] = options["validate_certs"]
        return data

    
    def dpkg_selections(self,options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "selection" in options and options["selection"] == "deinstall":
            data["delete"] = True
        return data
    
    def fail(self,options):
        data = {}
        return data
    
    def file(self,options, resolved_variables):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] =  options["path"]
        if "src" in options:
            data["file"] = options["src"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        if "mode" in options:
            data["mode"] = options["mode"]
            # if data["mode"] == "":
            #     data[""]
        if "file" not in data:
            return data
        for rv in resolved_variables:
            if "file" in data and type(data["file"]) is str:
                data, undetermined = self.resolved_variable_check(data, data["file"], rv)
                if undetermined:
                    data["undetermined_file"] = True   
        return data

    def find(self,options):
        data = {}
        return data

    def add_host(self,options):
        data = {}
        return data

    def apt_key(self,options):
        # res = {"category": "config_change" , "data": {},  "resolved_data": []}
        data = {}
        return data

    def apt_repository(self,options):
        data = {}
        return data
    
    def builtin_assert(self,options):
        data = {}
        return data

    def async_status(self,options):
        data = {}
        return data
    
    def gather_facts(self,options):
        data = {}
        return data
    
    def getent(self,options):
        data = {}
        return data

    def group(self,options):
        data = {}
        return data

    def group_by(self,options):
        data = {}
        return data

    def hostname(self,options):
        data = {}
        return data


    def meta(self,options):
        data = {}
        return data

    def package_facts(self,options):
        data = {}
        return data

    def pause(self,options):
        data = {}
        return data
    
    def ping(self,options):
        data = {}
        return data

    def reboot(self,options):
        data = {}
        return data

    def service_facts(self,options):
        data = {}
        return data
    
    def set_fact(self,options):
        data = {}
        return data

    def set_stats(self,options):
        data = {}
        return data

    def setup(self,options):
        data = {}
        return data

    def stat(self,options):
        data = {}
        return data

    def check_nest_variable(self, value, resolved_variables):
        # check nested variables
        variables = []
        for rv in resolved_variables:
            if rv["key"] not in value:
                continue
            if type(rv["value"]) is list:
                for v in rv["value"]:
                    key = "{{ " + rv["key"] + " }}"
                    if type(v) is dict:
                        v = json.dumps(v)
                    if "{{" in v:
                        variables.append(value.replace(key, v))
        return variables

    def resolved_variable_check(self, data, value, rv):
        undetermined = False
        if type(value) is not str:
            return data, undetermined
        if rv["key"] in value and "{{" in value:
            undetermined = True
            if rv["type"] in ["inventory_vars", "role_defaults", "role_vars", "special_vars"]:
                data["injection_risk"] = True
                if "injection_risk_variables" in data:
                    data["injection_risk_variables"].append(rv["key"])
                else:
                    data["injection_risk_variables"] = [rv["key"]]
        return data, undetermined