# -*- mode:python; coding:utf-8 -*-

# Copyright (c) 2022 IBM Corp. All rights reserved.
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

import pytest

from ansible_risk_insight.scanner import ARIScanner, config
from ansible_risk_insight.rules.R103_download_exec import DownloadExecRule


@pytest.mark.parametrize("type, name", [("project", "test/testdata/projects/my.collection")])
def test_scanner_with_project(type, name):
    ari_result, _ = _scan(type, name)
    assert ari_result
    role_result = ari_result.role(name="my.collection.sample-role-1")
    assert role_result
    task_result = role_result.task(name="Gcloud | Archive | Install into Path")
    assert task_result
    result = task_result.find_result(rule_id=DownloadExecRule.rule_id)
    assert result
    assert result.verdict
    assert result.detail["executed_file"]
    assert result.detail["executed_file"][0] == "{{ gcloud_archive_path }}/install.sh"


@pytest.mark.parametrize("type, name", [("collection", "community.mongodb")])
def test_scanner_with_collection(type, name):
    _, scandata = _scan(type, name)
    dep_names = [dep.get("name", "") for dep in scandata.findings.dependencies]
    assert len(dep_names) == 2
    assert "community.general" in dep_names
    assert "ansible.posix" in dep_names


@pytest.mark.parametrize("type, name", [("role", "test/testdata/roles/test_role")])
def test_scanner_with_role(type, name):
    ari_result, _ = _scan(type, name)
    assert ari_result
    role_result = ari_result.role(name="test_role")
    assert role_result
    task_result = role_result.task(name="execute the downloaded file")
    assert task_result
    result = task_result.find_result(rule_id=DownloadExecRule.rule_id)
    assert result
    assert result.verdict
    assert result.detail["executed_file"]
    assert result.detail["executed_file"][0] == "/etc/install.sh"


@pytest.mark.parametrize(
    "type, name, expected_line_numbers",
    [
        ("playbook", "test/testdata/files/test_line_number.yml", [[6, 13], [14, 18], [20, 23], [29, 33]]),
        ("playbook", "test/testdata/files/test_line_number2.yml", [[12, 15], [16, 17]]),
    ],
)
def test_scanner_line_number_detection(type, name, expected_line_numbers):
    ari_result, _ = _scan(type=type, name=name, playbook_only=True)
    assert ari_result
    playbook_result = ari_result.playbook(path=name)
    assert playbook_result
    task_results = playbook_result.tasks()
    for i, task_result in enumerate(task_results.nodes):
        assert task_result.node.spec.line_num_in_file
        detected = task_result.node.spec.line_num_in_file
        assert len(detected) == 2
        expected = expected_line_numbers[i]
        assert detected == expected


def _scan(type, name, **kwargs):
    if not kwargs:
        kwargs = {}
    kwargs["type"] = type
    kwargs["name"] = name

    s = ARIScanner(
        root_dir=config.data_dir,
        use_ansible_doc=False,
        read_ram=False,
        write_ram=False,
    )
    ari_result = s.evaluate(**kwargs)
    scandata = s.get_last_scandata()
    return ari_result, scandata
