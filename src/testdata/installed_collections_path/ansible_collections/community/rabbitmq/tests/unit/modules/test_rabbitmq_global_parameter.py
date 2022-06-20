# -*- coding: utf-8 -*-

from __future__ import (absolute_import, division, print_function)
__metaclass__ = type

from ansible_collections.community.rabbitmq.plugins.modules import rabbitmq_global_parameter

from ansible_collections.community.rabbitmq.tests.unit.compat.mock import patch
from ansible_collections.community.rabbitmq.tests.unit.modules.utils import AnsibleExitJson, AnsibleFailJson, ModuleTestCase, set_module_args


class TestRabbitMQGlobalParameterModule(ModuleTestCase):
    def setUp(self):
        super(TestRabbitMQGlobalParameterModule, self).setUp()
        self.module = rabbitmq_global_parameter

    def tearDown(self):
        super(TestRabbitMQGlobalParameterModule, self).tearDown()

    def _assert(self, exc, attribute, expected_value, msg=''):
        value = exc.message[attribute] if hasattr(exc, attribute) else exc.args[0][attribute]
        assert value == expected_value, msg

    def test_without_required_parameters(self):
        """Failure must occur when all parameters are missing."""
        with self.assertRaises(AnsibleFailJson):
            set_module_args({})
            self.module.main()

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_global_parameter.RabbitMqGlobalParameter._exec')
    def test_read_without_initial_global_parameters(self, _exec, get_bin_path):
        """Test that the code to read the global parameters does not fail anymore for RabbitMQ 3.7.x."""
        set_module_args({
            'name': 'cluster_name',
            'state': 'absent',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        # command list_global_parameters returns:
        # - RabbitMQ 3.6.x: ''
        # - RabbitMQ 3.7.x: '\n'
        # - RabbitMQ 3.8.x: 'name\tvalue\n' table header
        for out in '', '\n', 'name\tvalue\n':
            _exec.return_value = out.splitlines()
            try:
                self.module.main()
            except AnsibleExitJson as e:
                self._assert(e, 'changed', False)
                self._assert(e, 'state', 'absent')

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_global_parameter.RabbitMqGlobalParameter._exec')
    def test_remove_global_parameter(self, _exec, get_bin_path):
        """Test removal of global parameters."""
        set_module_args({
            'name': 'cluster_name',
            'state': 'absent',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        # command list_global_parameters returns:
        # - RabbitMQ 3.6.x: ''
        # - RabbitMQ 3.7.x: '\n'
        # - RabbitMQ 3.8.x: 'name\tvalue\n' table header
        for out in 'cluster_name\t"rabbitmq-test"', 'cluster_name\t"rabbitmq-test"\n', 'name\tvalue\ncluster_name\t"rabbitmq-test"\n':
            _exec.return_value = out.splitlines()
            try:
                self.module.main()
            except AnsibleExitJson as e:
                self._assert(e, 'changed', True)
                self._assert(e, 'state', 'absent')

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_global_parameter.RabbitMqGlobalParameter._exec')
    def test_set_global_parameter(self, _exec, get_bin_path):
        """Test setting of global parameters."""
        set_module_args({
            'name': 'cluster_name',
            'value': '"rabbitmq-test"',
            'state': 'present',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        versions = ['3.6', '3.7', '3.8']
        for version_num in versions:
            def side_effect(args, check_rc=True):
                if 'list_global_parameters' in args:
                    if version_num == '3.6':
                        return 'other_param\t"other_value"\ncluster_name\t"another_name"'.splitlines()
                    elif version_num == '3.7':
                        return 'other_param\t"other_value"\ncluster_name\t"another_name"\n'.splitlines()
                    else:
                        return 'name\tvalue\nother_param\t"other_value"\ncluster_name\t"another_name"\n'.splitlines()
                elif 'clear_global_parameter' in args or 'set_global_parameter' in args:
                    return ''.splitlines()
            _exec.side_effect = side_effect
            try:
                self.module.main()
            except AnsibleExitJson as e:
                self._assert(e, 'changed', True)
                self._assert(e, 'state', 'present')
                self._assert(e, 'value', 'rabbitmq-test')

    @patch('ansible.module_utils.basic.AnsibleModule.get_bin_path')
    @patch('ansible_collections.community.rabbitmq.plugins.modules.rabbitmq_global_parameter.RabbitMqGlobalParameter._exec')
    def test_set_no_change_global_parameter(self, _exec, get_bin_path):
        """Test that there is no change when setting the same global parameter."""
        set_module_args({
            'name': 'cluster_name',
            'value': '"rabbitmq-test"',
            'state': 'present',
        })
        get_bin_path.return_value = '/rabbitmqctl'

        def side_effect(args, check_rc=True):
            if 'list_global_parameters' in args:
                return 'other_param\t"other_value"\ncluster_name\t"rabbitmq-test"'.splitlines()
            elif 'clear_global_parameter' in args or 'set_global_parameter' in args:
                return ''.splitlines()
        _exec.side_effect = side_effect
        try:
            self.module.main()
        except AnsibleExitJson as e:
            self._assert(e, 'changed', False)
            self._assert(e, 'state', 'present')
            self._assert(e, 'value', 'rabbitmq-test')
