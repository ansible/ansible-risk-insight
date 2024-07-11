# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2024 RedHat. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from ansible_risk_insight.finder import update_the_yaml_target


def test_inline_replace_for_block_and_when():
    file_path = "test/testdata/inline_replace_data/block_and_when_play.yml"
    file_path_out = "test/testdata/inline_replace_data/block_and_when_play_fixed.yml"
    line_number = [
        "L6-11",
        "L12-20",
        "L23-30",
        "L31-34",
        "L39-46",
        "L47-50",
        "L55-61",
        "L62-65"
    ]
    new_content = [
        '''- name: Validate server authentication input provided by user\n  when:\n
            - (username is not defined or password is not defined) and (cert_file is not defined or key_file is not defined)
            and (auth_token is not defined)\n  ansible.builtin.fail:\n    msg: "username/password or cert_file/key_file or auth_token
            is mandatory"\n''',
        '''- name: Fail when more than one valid authentication method is provided\n  when:\n
            - ((username is defined or password is defined) and (cert_file is defined or key_file is defined) and
            auth_token is defined) or ((username is defined or password is defined) and (cert_file is defined or key_file is defined))
            or ((username is defined or password is defined) and auth_token is defined) or ((cert_file is defined or key_file is defined) and
            auth_token is defined)\n  ansible.builtin.fail:\n    msg: "Only one authentication method is allowed.
            Provide either username/password or cert_file/key_file or auth_token."\n''',
        '''        - ilo_network:\n            category: Systems\n            command: GetNetworkAdapters\n
            baseuri: "{{ baseuri }}"\n            username: "{{ username }}"\n            password: "{{ password }}"\n
            register: network_adapter_details\n''',
        '- name: Physical network adapter details in the server\n  ansible.builtin.debug:\n    msg: "{{ network_adapter_details }}"\n',
        '''        - ilo_network:\n            category: Systems\n            command: GetNetworkAdapters\n
            baseuri: "{{ baseuri }}"\n            cert_file: "{{ cert_file }}"\n            key_file: "{{ key_file }}"\n
            register: network_adapter_details\n''',
        '- name: Physical network adapter details present in the server\n  ansible.builtin.debug:\n    msg: "{{ network_adapter_details }}"\n',
        '''        - ilo_network:\n            category: Systems\n            command: GetNetworkAdapters\n
            baseuri: "{{ baseuri }}"\n            auth_token: "{{ auth_token }}"\n          register: network_adapter_details\n''',
        '- name: Physical network adapter details in the server\n  ansible.builtin.debug:\n    msg: "{{ network_adapter_details }}"\n'
    ]

    update_the_yaml_target(file_path, line_number, new_content)
    with open(file_path, 'r') as file:
        data = file.read()
    with open(file_path_out, 'r') as file:
        data_fixed = file.read()

    assert data == data_fixed
