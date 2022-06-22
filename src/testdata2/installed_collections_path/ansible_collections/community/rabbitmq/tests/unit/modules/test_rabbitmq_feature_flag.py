# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible_collections.community.rabbitmq.plugins.modules import rabbitmq_feature_flag

from ansible_collections.community.rabbitmq.tests.unit.compat.mock import patch
from ansible_collections.community.rabbitmq.tests.unit.modules.utils import AnsibleExitJson, AnsibleFailJson, ModuleTestCase, set_module_args


class TestRabbitMQFeatureFlagModule(ModuleTestCase):
    def setUp(self):
        super(TestRabbitMQFeatureFlagModule, self).setUp()
        self.module = rabbitmq_feature_flag

    def tearDown(self):
        super(TestRabbitMQFeatureFlagModule, self).tearDown()

    def _assert(self, exc, attribute, expected_value, msg=''):
        value = exc.message[attribute] if hasattr(exc, attribute) else exc.args[0][attribute]
        assert value == expected_value, msg

    def test_without_required_parameters(self):
        """Failure must occur when all parameters are missing."""
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            self.module.main()

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_feature_flag.RabbitMqFeatureFlag._exec')
    def test_enable_feature_flag(self, _exec, get_bin_path):
        """Test enabling feature flag."""
        set_module_args({
            'name': 'maintenance_mode_status',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        for out in 'name\tstate\nmaintenance_mode_status\tdisabled', 'name\tstate\nmaintenance_mode_status\tdisabled\n':
            _exec.return_value = out.splitlines()
            try:
                self.module.main()
            except AnsibleExitJson as e:
                self._assert(e, 'changed', True)

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_feature_flag.RabbitMqFeatureFlag._exec')
    def test_enable_no_change_feature_flag(self, _exec, get_bin_path):
        """Test that there is no change when enabling feature flag which is already enabled"""
        set_module_args({
            'name': 'maintenance_mode_status',
            'node': 'rabbit@node-1',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        for out in 'name\tstate\nmaintenance_mode_status\tenabled', 'name\tstate\nmaintenance_mode_status\tenabled\n':
            _exec.return_value = out.splitlines()
            try:
                self.module.main()
            except AnsibleExitJson as e:
                self._assert(e, 'changed', False)
