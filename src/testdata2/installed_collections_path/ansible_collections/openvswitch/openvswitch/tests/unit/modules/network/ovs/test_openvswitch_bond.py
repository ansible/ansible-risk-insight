#
# (c) 2020, James Denton <james.denton@outlook.com>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible.  If not, see <http://www.gnu.org/licenses/>.

# Make coding more python3-ish
from __future__ import absolute_import, division, print_function

__metaclass__ = type

from ansible_collections.openvswitch.openvswitch.tests.unit.compat.mock import (
    patch,
)
from ansible_collections.openvswitch.openvswitch.plugins.modules import (
    openvswitch_bond,
)
from ansible_collections.openvswitch.openvswitch.tests.unit.modules.utils import (
    set_module_args,
)
from .ovs_module import TestOpenVSwitchModule, load_fixture

test_name_side_effect_matrix = {
    "test_openvswitch_bond_absent_idempotent": [(0, "", "")],
    "test_openvswitch_bond_absent_removes_bond": [
        (0, "list_ports_bond_br.cfg", ""),
        (0, "get_port_bond0_other_config.cfg", ""),
        (0, "get_port_bond0_external_ids.cfg", ""),
        (0, "", ""),
        (0, "", ""),
    ],
    "test_openvswitch_bond_present_idempotent": [
        (0, "list_ports_bond_br.cfg", ""),
        (0, "get_port_bond0_other_config.cfg", ""),
        (0, "get_port_bond0_external_ids.cfg", ""),
        (0, "", ""),
        (0, "", ""),
    ],
    "test_openvswitch_bond_present_creates_bond": [
        (0, "", ""),
        (0, "", ""),
        (0, "", ""),
        (0, "", ""),
        (0, "", ""),
    ],
    "test_openvswitch_bond_present_creates_lacp_bond": [
        (0, "", ""),
        (0, "", ""),
        (0, "", ""),
        (0, "", ""),
        (0, "", ""),
    ],
}


class TestOpenVSwitchBondModule(TestOpenVSwitchModule):

    module = openvswitch_bond

    def setUp(self):
        super(TestOpenVSwitchBondModule, self).setUp()

        self.mock_run_command = patch(
            "ansible.module_utils.basic.AnsibleModule.run_command"
        )
        self.run_command = self.mock_run_command.start()
        self.mock_get_bin_path = patch(
            "ansible.module_utils.basic.AnsibleModule.get_bin_path"
        )
        self.get_bin_path = self.mock_get_bin_path.start()

    def tearDown(self):
        super(TestOpenVSwitchBondModule, self).tearDown()

        self.mock_run_command.stop()
        self.mock_get_bin_path.stop()

    def load_fixtures(self, test_name):
        test_side_effects = []
        for s in test_name_side_effect_matrix[test_name]:
            rc = s[0]
            out = s[1] if s[1] == "" else str(load_fixture(s[1]))
            err = s[2]
            side_effect_with_fixture_loaded = (rc, out, err)
            test_side_effects.append(side_effect_with_fixture_loaded)
        self.run_command.side_effect = test_side_effects

        self.get_bin_path.return_value = "/usr/bin/ovs-vsctl"

    def test_openvswitch_bond_absent_idempotent(self):
        set_module_args(dict(state="absent", bridge="bond-br", port="bond0"))
        self.execute_module(
            commands=[], test_name="test_openvswitch_bond_absent_idempotent"
        )

    def test_openvswitch_bond_absent_removes_bond(self):
        set_module_args(dict(state="absent", bridge="bond-br", port="bond0"))
        commands = ["/usr/bin/ovs-vsctl -t 5 del-port bond-br bond0"]
        self.execute_module(
            changed=True,
            commands=commands,
            test_name="test_openvswitch_bond_absent_removes_bond",
        )

    def test_openvswitch_bond_database_socket(self):
        set_module_args(
            dict(
                state="absent",
                bridge="bond-br",
                port="bond0",
                database_socket="unix:/opt/second.sock",
            )
        )
        commands = [
            "/usr/bin/ovs-vsctl --db=unix:/opt/second.sock -t 5 del-port bond-br bond0"
        ]
        self.execute_module(
            changed=True,
            commands=commands,
            test_name="test_openvswitch_bond_absent_removes_bond",
        )

    def test_openvswitch_bond_present_idempotent(self):
        set_module_args(
            dict(
                state="present",
                bridge="bond-br",
                port="bond0",
                external_ids={"foo": "bar"},
                other_config={"bond-detect-mode": "miimon"},
            )
        )
        self.execute_module(
            commands=[], test_name="test_openvswitch_bond_present_idempotent"
        )

    def test_openvswitch_bond_present_creates_bond(self):
        set_module_args(
            dict(
                state="present",
                bridge="bond-br",
                port="bond0",
                bond_updelay="100",
                bond_downdelay="100",
                interfaces=["eth3", "eth4"],
                other_config={"bond-detect-mode": "miimon"},
            )
        )
        commands = [
            "/usr/bin/ovs-vsctl -t 5 add-bond bond-br bond0 eth3 eth4"
            " bond_updelay=100 bond_downdelay=100",
            "/usr/bin/ovs-vsctl -t 5 set port bond0"
            " other_config:bond-detect-mode=miimon",
        ]
        self.execute_module(
            changed=True,
            commands=commands,
            test_name="test_openvswitch_bond_present_creates_bond",
        )

    def test_openvswitch_bond_present_creates_lacp_bond(self):
        set_module_args(
            dict(
                state="present",
                lacp="active",
                bridge="bond-br",
                port="bond0",
                interfaces=["eth3", "eth4"],
                other_config={"bond-detect-mode": "miimon"},
            )
        )
        commands = [
            "/usr/bin/ovs-vsctl -t 5 add-bond bond-br bond0 eth3 eth4"
            " lacp=active",
            "/usr/bin/ovs-vsctl -t 5 set port bond0"
            " other_config:bond-detect-mode=miimon",
        ]
        self.execute_module(
            changed=True,
            commands=commands,
            test_name="test_openvswitch_bond_present_creates_bond",
        )
