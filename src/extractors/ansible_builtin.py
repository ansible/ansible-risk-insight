import json
from extractors.base import Extractor


class AnsibleBuiltinExtractor(Extractor):
    name: str = "ansible.builtin"
    enabled: bool = True

    def match(self, task: dict) -> bool:
        resolved_name = task.get("resolved_name", "")
        return resolved_name.startswith("ansible.builtin.")

    def analyze(self, task: dict) -> dict:
        if not self.match(task):
            return task
        resolved_name = task.get("resolved_name", "")
        options = task.get("module_options", {})
        resolved_options = task.get("resolved_module_options", {})
        mutable_vars_per_mo = task.get("mutable_vars_per_mo", {})
        resolved_variables = task.get("resolved_variables", [])

        analyzed_data = []
        # builtin modules
        if resolved_name == "ansible.builtin.get_url":
            res = {
                "category": "inbound_transfer",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.get_url(options, mutable_vars_per_mo)
            for ro in resolved_options:
                res["resolved_data"].append(
                    self.get_url(ro, mutable_vars_per_mo)
                )
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.fetch":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.fetch(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.fetch(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.command":
            res = {"category": "cmd_exec", "data": {}, "resolved_data": []}
            res["data"] = self.command(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(
                    self.command(ro, resolved_variables)
                )
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.apt":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.apt(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.apt(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.add_host":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.add_host(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.add_host(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.apt_key":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.apt_key(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.apt_key(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.apt_repository":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.apt_repository(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.apt_repository(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.assemble":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.assemble(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.assemble(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.assert":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.builtin_assert(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.builtin_assert(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.async_status":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.async_status(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.async_status(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.blockinfile":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.blockinfile(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.blockinfile(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.copy":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.copy(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.copy(ro, resolved_variables))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.cron":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.cron(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.cron(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.debconf":
            res = {
                "category": "config_change",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.debconf(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.debconf(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.debug":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.debug(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.debug(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.dnf":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.dnf(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.dnf(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.dpkg_selections":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.dpkg_selections(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.dpkg_selections(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.expect":
            res = {"category": "cmd_exec", "data": {}, "resolved_data": []}
            res["data"] = self.expect(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(
                    self.expect(ro, resolved_variables)
                )
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.fail":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.fail(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.fail(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.file":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.file(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.file(ro, resolved_variables))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.find":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.find(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.find(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.gather_facts":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.gather_facts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.gather_facts(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.getent":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.getent(options)
            res["resolved_data"] = self.getent(resolved_options)
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.git":
            res = {
                "category": "inbound_transfer",
                "data": {},
                "resolved_data": [],
            }
            res["data"], res["category"] = self.git(
                options, mutable_vars_per_mo
            )
            for ro in resolved_options:
                rd, c = self.git(ro, mutable_vars_per_mo)
                res["resolved_data"].append(rd)
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.group":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.group(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.group(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.group_by":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.group_by(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.group_by(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.hostname":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.hostname(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.hostname(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.iptables":
            res = {
                "category": "network_change",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.iptables(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.iptables(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.known_hosts":
            res = {
                "category": "network_change",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.known_hosts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.known_hosts(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.lineinfile":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.lineinfile(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.lineinfile(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.meta":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.meta(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.meta(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.package":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.package(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.package(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.package_facts":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.package_facts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.package_facts(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.pause":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.pause(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.pause(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.ping":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.ping(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.ping(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.pip":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.pip(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.pip(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.raw":
            res = {"category": "cmd_exec", "data": {}, "resolved_data": []}
            res["data"] = self.raw(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(self.raw(ro, resolved_variables))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.reboot":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.reboot(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.reboot(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.replace":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.replace(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.replace(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.rpm_key":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.rpm_key(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.rpm_key(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.script":
            res = {"category": "cmd_exec", "data": {}, "resolved_data": []}
            res["data"] = self.script(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(
                    self.script(ro, resolved_variables)
                )
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.service":
            res = {
                "category": "system_change",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.service(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.service(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.service_facts":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.service_facts(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.service_facts(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.set_fact":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.set_fact(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.set_fact(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.set_stats":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.set_stats(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.set_stats(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.setup":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.setup(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.setup(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.slurp":
            res = {
                "category": "inbound_transfer",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.slurp(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.slurp(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.stat":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.stat(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.stat(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.subversion":
            res = {
                "category": "inbound_transfer",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.subversion(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.subversion(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.sysvinit":
            res = {
                "category": "system_change",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.sysvinit(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.sysvinit(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.systemd":
            res = {
                "category": "system_change",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.systemd(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.systemd(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.tempfile":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.tempfile(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.tempfile(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.template":
            res = {"category": "file_change", "data": {}, "resolved_data": []}
            res["data"] = self.template(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.template(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.unarchive":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"], res["category"] = self.unarchive(
                options, resolved_options, mutable_vars_per_mo
            )
            for ro in resolved_options:
                rores, _ = self.unarchive(
                    ro, resolved_options, mutable_vars_per_mo
                )
                res["resolved_data"].append(rores)
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.uri":
            res = {
                "category": "inbound_transfer",
                "data": {},
                "resolved_data": [],
            }
            res["data"], res["category"] = self.uri(
                options, mutable_vars_per_mo
            )
            for ro in resolved_options:
                rd, c = self.uri(ro, mutable_vars_per_mo)
                res["resolved_data"].append(rd)
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.user":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.user(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.user(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.validate_argument_spec":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.validate_argument_spec(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.validate_argument_spec(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.wait_for":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.wait_for(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.wait_for(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.wait_for_connection":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.wait_for_connection(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.wait_for_connection(ro))
            res = self.wait_for_connection(task)
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.yum":
            res = {
                "category": "package_install",
                "data": {},
                "resolved_data": [],
            }
            res["data"] = self.yum(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.yum(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.yum_repository":
            res = {"category": "", "data": {}, "resolved_data": []}
            res["data"] = self.yum_repository(options)
            for ro in resolved_options:
                res["resolved_data"].append(self.yum_repository(ro))
            analyzed_data.append(res)

        if resolved_name == "ansible.builtin.shell":
            res = {"category": "cmd_exec", "data": {}, "resolved_data": []}
            res["data"] = self.shell(options, resolved_variables)
            for ro in resolved_options:
                res["resolved_data"].append(
                    self.shell(ro, resolved_variables)
                )
            analyzed_data.append(res)

        if len(analyzed_data) != 0:
            # root
            res = self.root(task)
            if res["data"]["root"]:
                analyzed_data.append(res)

        task["analyzed_data"] = analyzed_data

        return task

    def root(self, task):
        is_root = False
        if "become" in task["options"] and task["options"]["become"]:
            is_root = True
        res = {"category": "privilege_escalation", "data": {"root": is_root}}
        return res

    def get_url(self, options, mutable_vars_per_mo):
        data = {}
        mutable_vars_per_type = {}
        # original options
        if type(options) is not dict:
            return data
        if "url" in options:
            data["src"] = options["url"]
            mutable_vars_per_type["src"] = mutable_vars_per_mo.get("url", [])
        if "dest" in options:
            data["dest"] = options["dest"]
            mutable_vars_per_type["dest"] = mutable_vars_per_mo.get(
                "dest", []
            )
        if "mode" in options:
            # todo: check if octal number
            data["mode"] = options["mode"]
        if "checksum" in options:
            data["checksum"] = options["checksum"]
        if "validate_certs" in options:
            if (
                not options["validate_certs"]
                or options["validate_certs"] == "no"
            ):
                data["validate_certs"] = False
        # injection risk
        if "src" in data and type(data["src"]) is str:
            mutable_vars = mutable_vars_per_type.get("src", [])
            if len(mutable_vars) > 0:
                data = self.embed_mutable_vars(
                    data, mutable_vars, "undetermined_src", "mutable_src_vars"
                )
        if "dest" in data and type(data["dest"]) is str:
            mutable_vars = mutable_vars_per_type.get("dest", [])
            if len(mutable_vars) > 0:
                data = self.embed_mutable_vars(
                    data,
                    mutable_vars,
                    "undetermined_dest",
                    "mutable_dest_vars",
                )
        # unsecure src/dest

        return data

    def fetch(self, options):
        data = {}
        if type(options) is not dict:
            return data
        data["src"] = options["src"]
        data["dest"] = options["dest"]
        return data

    def command(self, options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] = options
        else:
            if "cmd" in options:
                data["cmd"] = options["cmd"]
            if "argv" in options:
                data["cmd"] = options["argv"]
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["cmd"], rv
                )
                if undetermined:
                    data["undetermined_cmd"] = True
        return data

    def apt(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "pkg" in options:
            data["pkg"] = options["pkg"]
        if "name" in options:
            data["pkg"] = options["name"]
        if "package" in options:
            data["pkg"] = options["package"]
        if "deb" in options:
            data["pkg"] = options["deb"]
        if (
            "allow_unauthenticated" in options
            and options["allow_unauthenticated"]
        ):
            data["unauthenticated"] = True
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data

    def assemble(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "dest" in options:
            data["file"] = options["dest"]
        if "src" in options:
            data["content"] = options["src"]
        if "mode" in options:
            data["mode"] = options["mode"]
        return data

    def blockinfile(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] = options["path"]
        if "dest" in options:
            data["file"] = options["dest"]
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
            data["dest"] = options["dest"]
        if "src" in options:
            data["src"] = options["src"]
        if "content" in options:
            data["src"] = options["content"]
        if "mode" in options:
            data["mode"] = options["mode"]
        for rv in resolved_variables:
            if "dest" in data and type(data["dest"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["dest"], rv
                )
                if undetermined:
                    data["undetermined_dest"] = True
            if "src" in data and type(data["src"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["src"], rv
                )
                if undetermined:
                    data["undetermined_src"] = True
        return data

    def git(self, options, mutable_vars_per_mo):
        data = {}
        category = "inbound_transfer"
        mutable_vars_per_type = {}
        if type(options) is not dict:
            return data
        if "repo" in options:
            data["src"] = options["repo"]
            mutable_vars_per_type["src"] = mutable_vars_per_mo.get("repo", [])
        if "dest" in options:
            data["dest"] = options["dest"]
            mutable_vars_per_type["dest"] = mutable_vars_per_mo.get(
                "dest", []
            )
        if "version" in options:
            data["version"] = options["version"]
        if "clone" in options and (
            not options["clone"] or options["clone"] == "no"
        ):
            category = ""
            return data, category
        if "update" in options and (
            not options["update"] or options["update"] == "no"
        ):
            category = ""
            return data, category
        # injection risk
        if "src" in data and type(data["src"]) is str:
            mutable_vars = mutable_vars_per_type.get("src", [])
            if len(mutable_vars) > 0:
                data = self.embed_mutable_vars(
                    data, mutable_vars, "undetermined_src", "mutable_src_vars"
                )
        if "dest" in data and type(data["dest"]) is str:
            mutable_vars = mutable_vars_per_type.get("dest", [])
            if len(mutable_vars) > 0:
                data = self.embed_mutable_vars(
                    data,
                    mutable_vars,
                    "undetermined_dest",
                    "mutable_dest_vars",
                )
        return data, category

    def iptables(self, options):
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

    def known_hosts(self, options):
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

    def lineinfile(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "dest" in options:
            data["file"] = options["dest"]
        if "path" in options:
            data["file"] = options["path"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        if "line" in options:
            data["content"] = options["line"]
        if "mode" in options:
            data["mode"] = options["mode"]
        return data

    def package(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data

    def pip(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data

    def raw(self, options, resolved_variables):
        data = {}
        if type(options) is str:
            data["cmd"] = options
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["cmd"], rv
                )
                if undetermined:
                    data["undetermined_cmd"] = True
        return data

    def replace(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "replace" in options:
            data["content"] = options["replace"]  # after
        if "regexp" in options:
            data["regexp"] = options["regexp"]  # before
        if "path" in options:
            data["file"] = options["path"]
        if "dest" in options:
            data["file"] = options["dest"]
        if "mode" in options:
            data["mode"] = options["mode"]
        if "unsafe_writes" in options and options["unsafe_writes"]:
            data["unsafe_writes"] = True
        return data

    def rpm_key(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "key" in options:
            data["file"] = options["key"]
        if "state" in options and options["state"] == "absent":
            data["delete"] = True
        return data

    def script(self, options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] = options
        else:
            if "cmd" in options:
                data["cmd"] = options["cmd"]
        if "cmd" not in data:
            return data
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["cmd"], rv
                )
                if undetermined:
                    data["undetermined_cmd"] = True
        return data

    # proxy for multiple more specific service manager modules
    def service(self, options):
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

    def sysvinit(self, options):
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

    def shell(self, options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] = options
        else:
            if "cmd" in options:
                data["cmd"] = options["cmd"]
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["cmd"], rv
                )
                if undetermined:
                    data["undetermined_cmd"] = True
        return data

    def slurp(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "src" in options:
            data["src"] = options["src"]
        if "path" in options:
            data["src"] = options["path"]
        return data

    def subversion(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "repo" in options:
            data["src"] = options["repo"]
        if "dest" in options:
            data["dest"] = options["dest"]
        return data

    def systemd(self, options):
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

    def tempfile(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] = options["path"]
        if "prefix" in options:
            data["file"] = options["prefix"]
        if "suffix" in options:
            data["file"] = options["suffix"]
        return data

    def template(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "src" in options:
            data["content"] = options["src"]
        if "dest" in options:
            data["file"] = options["dest"]
        if "mode" in options:
            data["mode"] = options["mode"]
        if "group" in options:
            data["group"] = options["group"]
        if "owner" in options:
            data["owner"] = options["owner"]
        if "unsafe_writes" in options and options["unsafe_writes"]:
            data["unsafe_writes"] = True
        return data

    def uri(self, options, mutable_vars_per_mo):
        category = ""
        data = {}
        mutable_vars_per_type = {}
        if type(options) is not dict:
            return data, category
        if "method" in options and (
            options["method"] == "POST"
            or options["method"] == "PUT"
            or options["method"] == "PATCH"
        ):
            category = "outbound_transfer"
            if "url" in options:
                data["dest"] = options["url"]
                mutable_vars_per_type["dest"] = mutable_vars_per_mo.get(
                    "url", []
                )
            if "dest" in data and type(data["dest"]) is str:
                mutable_vars = mutable_vars_per_type.get("dest", [])
                if len(mutable_vars) > 0:
                    data = self.embed_mutable_vars(
                        data,
                        mutable_vars,
                        "undetermined_dest",
                        "mutable_dest_vars",
                    )
        elif "method" in options and options["method"] == "GET":
            if "url" in options:
                data["src"] = options["url"]
                mutable_vars_per_type["src"] = mutable_vars_per_mo.get(
                    "url", []
                )
            if "dest" in options:
                data["dest"] = options["dest"]
                mutable_vars_per_type["dest"] = mutable_vars_per_mo.get(
                    "dest", []
                )
            if "validate_certs" in options:
                data["validate_certs"] = options["validate_certs"]
            if "unsafe_writes" in options:
                data["unsafe_writes"] = options["unsafe_writes"]
            # injection risk
            if "src" in data and type(data["src"]) is str:
                mutable_vars = mutable_vars_per_type.get("src", [])
                if len(mutable_vars) > 0:
                    data = self.embed_mutable_vars(
                        data,
                        mutable_vars,
                        "undetermined_src",
                        "mutable_src_vars",
                    )
            if "dest" in data and type(data["dest"]) is str:
                mutable_vars = mutable_vars_per_type.get("dest", [])
                if len(mutable_vars) > 0:
                    data = self.embed_mutable_vars(
                        data,
                        mutable_vars,
                        "undetermined_dest",
                        "mutable_dest_vars",
                    )
        return data, category

    def validate_argument_spec(self, options):
        data = {}
        return data

    def wait_for(self, options):
        data = {}
        return data

    def wait_for_connection(self, options):
        data = {}
        return data

    def yum(self, options):
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

    def yum_repository(self, options):
        data = {}
        return data

    def user(self, options):  # config change?
        data = {}
        return data

    def unarchive(self, options, resolved_options, mutable_vars_per_mo):
        category = ""
        data = {}
        mutable_vars_per_type = {}
        if type(options) is not dict:
            return data, category
        if "dest" in options:
            data["dest"] = options["dest"]
            mutable_vars_per_type["dest"] = mutable_vars_per_mo.get(
                "dest", []
            )
        if "src" in options:
            data["src"] = options["src"]
            mutable_vars_per_type["src"] = mutable_vars_per_mo.get("src", [])
        if "remote_src" in options:  # if yes, don't copy
            data["remote_src"] = options["remote_src"]
        if "unsafe_writes" in options:
            data["unsafe_writes"] = options["unsafe_writes"]
        if "validate_certs" in options:
            data["validate_certs"] = options["validate_certs"]

        # set category
        # if remote_src=yes and src contains :// => inbound_transfer
        if "remote_src" in data and (
            data["remote_src"] == "yes" or data["remote_src"]
        ):
            if (
                "src" in data
                and type(data["src"]) is str
                and "://" in data["src"]
            ):
                category = "inbound_transfer"
        # check resolved option
        for ro in resolved_options:
            if "remote_src" in ro and (
                ro["remote_src"] == "yes" or ro["remote_src"]
            ):
                if (
                    "src" in ro
                    and type(ro["src"]) is str
                    and "://" in ro["src"]
                ):
                    category = "inbound_transfer"

        if "src" in data and type(data["src"]) is str:
            mutable_vars = mutable_vars_per_type.get("src", [])
            if len(mutable_vars) > 0:
                data = self.embed_mutable_vars(
                    data, mutable_vars, "undetermined_src", "mutable_src_vars"
                )
        if "dest" in data and type(data["dest"]) is str:
            mutable_vars = mutable_vars_per_type.get("dest", [])
            if len(mutable_vars) > 0:
                data = self.embed_mutable_vars(
                    data,
                    mutable_vars,
                    "undetermined_dest",
                    "mutable_dest_vars",
                )
        return data, category

    def cron(self, options):
        data = {}
        return data

    def debconf(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "question" in options:
            data["config"] = options["question"]
        return data

    def debug(self, options):
        data = {}
        return data

    def expect(self, options, resolved_variables):
        data = {}
        if type(options) is not dict:
            data["cmd"] = options
        else:
            if "command" in options:
                data["cmd"] = options["command"]
        for rv in resolved_variables:
            if "cmd" in data and type(data["cmd"]) is str:
                data, undetermined = self.resolved_variable_check(
                    data, data["cmd"], rv
                )
                if undetermined:
                    data["undetermined_cmd"] = True
        return data

    def dnf(self, options):
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

    def dpkg_selections(self, options):
        data = {}
        if type(options) is not dict:
            return data
        if "name" in options:
            data["pkg"] = options["name"]
        if "selection" in options and options["selection"] == "deinstall":
            data["delete"] = True
        return data

    def fail(self, options):
        data = {}
        return data

    def file(self, options, resolved_variables):
        data = {}
        if type(options) is not dict:
            return data
        if "path" in options:
            data["file"] = options["path"]
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
                data, undetermined = self.resolved_variable_check(
                    data, data["file"], rv
                )
                if undetermined:
                    data["undetermined_file"] = True
        return data

    def find(self, options):
        data = {}
        return data

    def add_host(self, options):
        data = {}
        return data

    def apt_key(self, options):
        data = {}
        return data

    def apt_repository(self, options):
        data = {}
        return data

    def builtin_assert(self, options):
        data = {}
        return data

    def async_status(self, options):
        data = {}
        return data

    def gather_facts(self, options):
        data = {}
        return data

    def getent(self, options):
        data = {}
        return data

    def group(self, options):
        data = {}
        return data

    def group_by(self, options):
        data = {}
        return data

    def hostname(self, options):
        data = {}
        return data

    def meta(self, options):
        data = {}
        return data

    def package_facts(self, options):
        data = {}
        return data

    def pause(self, options):
        data = {}
        return data

    def ping(self, options):
        data = {}
        return data

    def reboot(self, options):
        data = {}
        return data

    def service_facts(self, options):
        data = {}
        return data

    def set_fact(self, options):
        data = {}
        return data

    def set_stats(self, options):
        data = {}
        return data

    def setup(self, options):
        data = {}
        return data

    def stat(self, options):
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
            if rv["type"] in [
                "inventory_vars",
                "role_defaults",
                "role_vars",
                "special_vars",
            ]:
                data["injection_risk"] = True
                if "injection_risk_variables" in data:
                    data["injection_risk_variables"].append(rv["key"])
                else:
                    data["injection_risk_variables"] = [rv["key"]]
        return data, undetermined

    def embed_mutable_vars(self, data, mutable_vars, key="", vars_key=""):
        if len(mutable_vars) == 0:
            return data
        data["injection_risk"] = True
        injection_risk_vars = [mv for mv in mutable_vars if mv != ""]
        if "injection_risk_variables" not in data:
            data["injection_risk_variables"] = []
        data["injection_risk_variables"].extend(injection_risk_vars)
        if key != "":
            data[key] = True
        if vars_key != "":
            if vars_key not in data:
                data[vars_key] = []
            data[vars_key].extend(injection_risk_vars)
        return data
