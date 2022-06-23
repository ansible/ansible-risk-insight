#
# Copyright: (c) 2021, Abhijeet Kasurde <akasurde@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible_collections.community.general.tests.unit.compat.mock import call, patch
from ansible_collections.community.general.plugins.modules.packaging.language import npm
from ansible_collections.community.general.tests.unit.plugins.modules.utils import (
    AnsibleExitJson, AnsibleFailJson, ModuleTestCase, set_module_args)


class NPMModuleTestCase(ModuleTestCase):
    module = npm

    def setUp(self):
        super(NPMModuleTestCase, self).setUp()
        ansible_module_path = "ansible_collections.community.general.plugins.modules.packaging.language.npm.AnsibleModule"
        self.mock_run_command = patch('%s.run_command' % ansible_module_path)
        self.module_main_command = self.mock_run_command.start()
        self.mock_get_bin_path = patch('%s.get_bin_path' % ansible_module_path)
        self.get_bin_path = self.mock_get_bin_path.start()
        self.get_bin_path.return_value = '/testbin/npm'

    def tearDown(self):
        self.mock_run_command.stop()
        self.mock_get_bin_path.stop()
        super(NPMModuleTestCase, self).tearDown()

    def module_main(self, exit_exc):
        with self.assertRaises(exit_exc) as exc:
            self.module.main()
        return exc.exception.args[0]

    def test_present(self):
        set_module_args({
            'name': 'coffee-script',
            'global': 'true',
            'state': 'present'
        })
        self.module_main_command.side_effect = [
            (0, '{}', ''),
            (0, '{}', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(['/testbin/npm', 'list', '--json', '--long', '--global'], check_rc=False, cwd=None),
        ])

    def test_absent(self):
        set_module_args({
            'name': 'coffee-script',
            'global': 'true',
            'state': 'absent'
        })
        self.module_main_command.side_effect = [
            (0, '{"dependencies": {"coffee-script": {}}}', ''),
            (0, '{}', ''),
        ]

        result = self.module_main(AnsibleExitJson)

        self.assertTrue(result['changed'])
        self.module_main_command.assert_has_calls([
            call(['/testbin/npm', 'uninstall', '--global', 'coffee-script'], check_rc=True, cwd=None),
        ])
