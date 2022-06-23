# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible_collections.community.rabbitmq.plugins.modules import rabbitmq_upgrade

from ansible_collections.community.rabbitmq.tests.unit.compat.mock import patch
from ansible_collections.community.rabbitmq.tests.unit.modules.utils import AnsibleExitJson, AnsibleFailJson, ModuleTestCase, set_module_args


class TestRabbitMQUpgradeModule(ModuleTestCase):
    def setUp(self):
        super(TestRabbitMQUpgradeModule, self).setUp()
        self.module = rabbitmq_upgrade

    def tearDown(self):
        super(TestRabbitMQUpgradeModule, self).tearDown()

    def _assert(self, exc, attribute, expected_value, msg=''):
        value = exc.message[attribute] if hasattr(exc, attribute) else exc.args[0][attribute]
        assert value == expected_value, msg

    def test_without_required_parameters(self):
        """Failure must occur when all parameters are missing."""
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            self.module.main()

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_without_maitenance_mode_status_feature_flag(self, _exec, get_bin_path):
        """Failure must occur when maintenance_mode_status feature_flag is disabled/not available"""
        with self.assertRaises(AnsibleFailJson):
            set_module_args({
                'action': 'drain',
                'node': 'rabbit@node-1',
            })
            get_bin_path.return_value = '/rabbitmqctl'

            def side_effect(*args, **kwargs):
                if args[0] == 'rabbitmq-diagnostics':
                    out = '{"active_plugins": ["rabbitmq_management", "amqp_client", "rabbitmq_web_dispatch", "cowboy",'\
                          '"cowlib", "rabbitmq_management_agent"], "is_under_maintenance": false}'
                elif args[0] == 'rabbitmqctl':
                    out = 'name\tstate\nmaintenance_mode_status\tdisabled'
                else:
                    out = ''
                return out.splitlines()

            _exec.side_effect = side_effect
            self.module.main()

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_drain_node(self, _exec, get_bin_path):
        """Execute action: drain on active node"""
        set_module_args({
            'action': 'drain',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        def side_effect(*args, **kwargs):
            if args[0] == 'rabbitmq-diagnostics':
                out = '{"active_plugins": ["rabbitmq_management", "amqp_client", "rabbitmq_web_dispatch", "cowboy",'\
                      '"cowlib", "rabbitmq_management_agent"], "is_under_maintenance": false}'
            elif args[0] == 'rabbitmqctl':
                out = 'name\tstate\nmaintenance_mode_status\tenabled'
            else:
                out = ''
            return out.splitlines()

        _exec.side_effect = side_effect
        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', True)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_no_change_drain_node(self, _exec, get_bin_path):
        """Execute action: drain on already disabled node"""
        set_module_args({
            'action': 'drain',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        def side_effect(*args, **kwargs):
            if args[0] == 'rabbitmq-diagnostics':
                out = '{"active_plugins": ["rabbitmq_management", "amqp_client", "rabbitmq_web_dispatch", "cowboy",'\
                      '"cowlib", "rabbitmq_management_agent"], "is_under_maintenance": true}'
            elif args[0] == 'rabbitmqctl':
                out = 'name\tstate\nmaintenance_mode_status\tenabled'
            else:
                out = ''
            return out.splitlines()

        _exec.side_effect = side_effect
        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', False)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_revive_node(self, _exec, get_bin_path):
        """Execute action: revive on disabled node"""
        set_module_args({
            'action': 'revive',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        def side_effect(*args, **kwargs):
            if args[0] == 'rabbitmq-diagnostics':
                out = '{"active_plugins": ["rabbitmq_management", "amqp_client", "rabbitmq_web_dispatch", "cowboy",'\
                      '"cowboy", "cowlib", "rabbitmq_management_agent"], "is_under_maintenance": true}'
            elif args[0] == 'rabbitmqctl':
                out = 'name\tstate\nmaintenance_mode_status\tenabled'
            else:
                out = ''
            return out.splitlines()

        _exec.side_effect = side_effect
        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', True)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_no_change_revive_node(self, _exec, get_bin_path):
        """Execute action: revive on active node"""
        set_module_args({
            'action': 'revive',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        def side_effect(*args, **kwargs):
            if args[0] == 'rabbitmq-diagnostics':
                out = '{"active_plugins": ["rabbitmq_management", "amqp_client", "rabbitmq_web_dispatch", "cowboy",'\
                      '"cowlib", "rabbitmq_management_agent"], "is_under_maintenance": false}'
            elif args[0] == 'rabbitmqctl':
                out = 'name\tstate\nmaintenance_mode_status\tenabled'
            else:
                out = ''
            return out.splitlines()

        _exec.side_effect = side_effect
        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', False)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_await_online_quorum_plus_one(self, _exec, get_bin_path):
        """Execute action: await_online_quorum_plus_one"""
        set_module_args({
            'action': 'await_online_quorum_plus_one',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', True)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_await_online_synchronized_mirror(self, _exec, get_bin_path):
        """Execute action: await_online_synchronized_mirror"""
        set_module_args({
            'action': 'await_online_synchronized_mirror',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', True)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_upgrade.RabbitMqUpgrade._exec')
    def test_post_upgrade(self, _exec, get_bin_path):
        """Execute action: post_upgrade"""
        set_module_args({
            'action': 'post_upgrade',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', True)
