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
    s = _scan(type, name)
    risk_found_role_count = s.findings.report.get("summary", {}).get("roles", {}).get("risk_found", -1)
    assert risk_found_role_count > 0
    details = s.findings.report.get("details", [])
    assert len(details) > 0
    results = details[0].get("results", [])
    assert len(results) > 0
    download_exec_result = [r for r in results if r.get("rule", {}).get("name", "") == DownloadExecRule.name]
    assert len(download_exec_result) > 0


@pytest.mark.parametrize("type, name", [("collection", "community.mongodb")])
def test_scanner_with_collection(type, name):
    s = _scan(type, name)
    dep_names = [dep.get("name", "") for dep in s.findings.dependencies]
    assert len(dep_names) == 2
    assert "community.general" in dep_names
    assert "ansible.posix" in dep_names


@pytest.mark.parametrize("type, name", [("role", "test/testdata/roles/test_role")])
def test_scanner_with_role(type, name):
    s = _scan(type, name)
    risk_found_role_count = s.findings.report.get("summary", {}).get("roles", {}).get("risk_found", -1)
    assert risk_found_role_count > 0
    details = s.findings.report.get("details", [])
    assert len(details) > 0
    results = details[0].get("results", [])
    assert len(results) > 0
    download_exec_result = [r for r in results if r.get("rule", {}).get("name", "") == DownloadExecRule.name]
    assert len(download_exec_result) > 0


def _scan(type, name):
    s = ARIScanner(
        root_dir=config.data_dir,
        use_ansible_doc=False,
    )
    s.evaluate(
        type=type,
        name=name,
    )
    return s.get_last_scandata()
