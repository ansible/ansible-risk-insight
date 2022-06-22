.. _openvswitch.openvswitch.openvswitch_db_module:


**************************************
openvswitch.openvswitch.openvswitch_db
**************************************

**Configure open vswitch database.**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Set column values in record in database table.



Requirements
------------
The below requirements are needed on the host that executes this module.

- ovs-vsctl >= 2.3.3


Parameters
----------

.. raw:: html

    <table  border=0 cellpadding=0 class="documentation-table">
        <tr>
            <th colspan="1">Parameter</th>
            <th>Choices/<font color="blue">Defaults</font></th>
            <th width="100%">Comments</th>
        </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>col</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Identifies the column in the record.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>key</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Identifies the key in the record column, when the column is a map type.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>record</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Identifies the record in the table.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>state</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li><div style="color: blue"><b>present</b>&nbsp;&larr;</div></li>
                                    <li>absent</li>
                                    <li>read</li>
                        </ul>
                </td>
                <td>
                        <div>Configures the state of the key. When set to <em>present</em>, the <em>key</em> and <em>value</em> pair will be set on the <em>record</em> and when set to <em>absent</em> the <em>key</em> will not be set.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>table</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Identifies the table in the database.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>timeout</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">5</div>
                </td>
                <td>
                        <div>How long to wait for ovs-vswitchd to respond</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>value</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Expected value for the table, record, column and key.</div>
                </td>
            </tr>
    </table>
    <br/>




Examples
--------

.. code-block:: yaml

    # Increase the maximum idle time to 50 seconds before pruning unused kernel
    # rules.
    - openvswitch.openvswitch.openvswitch_db:
        table: open_vswitch
        record: .
        col: other_config
        key: max-idle
        value: 50000

    # Disable in band copy
    - openvswitch.openvswitch.openvswitch_db:
        table: Bridge
        record: br-int
        col: other_config
        key: disable-in-band
        value: true

    # Remove in band key
    - openvswitch.openvswitch.openvswitch_db:
        state: present
        table: Bridge
        record: br-int
        col: other_config
        key: disable-in-band

    # Mark port with tag 10
    - openvswitch.openvswitch.openvswitch_db:
        table: Port
        record: port0
        col: tag
        value: 10




Status
------


Authors
~~~~~~~

- Mark Hamilton (@markleehamilton) <mhamilton@vmware.com>
