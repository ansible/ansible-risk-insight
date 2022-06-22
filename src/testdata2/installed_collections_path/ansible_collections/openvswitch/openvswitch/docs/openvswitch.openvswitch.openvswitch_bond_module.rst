.. _openvswitch.openvswitch.openvswitch_bond_module:


****************************************
openvswitch.openvswitch.openvswitch_bond
****************************************

**Manage Open vSwitch bonds**


Version added: 1.0.0

.. contents::
   :local:
   :depth: 1


Synopsis
--------
- Manage Open vSwitch bonds and associated options.



Requirements
------------
The below requirements are needed on the host that executes this module.

- ovs-vsctl


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
                    <b>bond_downdelay</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Number of milliseconds a link must be down to be deactivated to prevent flapping.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>bond_mode</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li>active-backup</li>
                                    <li>balance-tcp</li>
                                    <li>balance-slb</li>
                        </ul>
                </td>
                <td>
                        <div>Sets the bond mode</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>bond_updelay</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">integer</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Number of milliseconds a link must be up to be activated to prevent flapping.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>bridge</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Name of bridge to manage</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>external_ids</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">{}</div>
                </td>
                <td>
                        <div>Dictionary of external_ids applied to a port.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>interfaces</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>List of interfaces to add to the bond</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>lacp</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                    </div>
                </td>
                <td>
                        <ul style="margin: 0; padding: 0"><b>Choices:</b>
                                    <li>active</li>
                                    <li>passive</li>
                                    <li>off</li>
                        </ul>
                </td>
                <td>
                        <div>Sets LACP mode</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>other_config</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">dictionary</span>
                    </div>
                </td>
                <td>
                        <b>Default:</b><br/><div style="color: blue">{}</div>
                </td>
                <td>
                        <div>Dictionary of other_config applied to a port.</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>port</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">string</span>
                         / <span style="color: red">required</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Name of port to manage on the bridge</div>
                </td>
            </tr>
            <tr>
                <td colspan="1">
                    <div class="ansibleOptionAnchor" id="parameter-"></div>
                    <b>set</b>
                    <a class="ansibleOptionLink" href="#parameter-" title="Permalink to this option"></a>
                    <div style="font-size: small">
                        <span style="color: purple">list</span>
                         / <span style="color: purple">elements=string</span>
                    </div>
                </td>
                <td>
                </td>
                <td>
                        <div>Sets one or more properties on a port.</div>
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
                        </ul>
                </td>
                <td>
                        <div>Whether the port should exist</div>
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
                        <div>How long to wait for ovs-vswitchd to respond in seconds</div>
                </td>
            </tr>
    </table>
    <br/>




Examples
--------

.. code-block:: yaml

    - name: Create an active-backup bond using eth4 and eth5 on bridge br-ex
      openvswitch.openvswitch.openvswitch_bond:
        bridge: br-ex
        port: bond1
        interfaces:
          - eth4
          - eth5
        state: present
    - name: Delete the bond from bridge br-ex
      openvswitch.openvswitch.openvswitch_bond:
        bridge: br-ex
        port: bond1
        state: absent
    - name: Create an active LACP bond using eth4 and eth5 on bridge br-ex
      openvswitch.openvswitch.openvswitch_bond:
        bridge: br-ex
        port: bond1
        interfaces:
          - eth4
          - eth5
        lacp: active
        state: present
    # NOTE: other_config values of integer type must be represented
    # as literal strings
    - name: Configure bond with miimon link monitoring at 100 millisecond intervals
      openvswitch.openvswitch.openvswitch_bond:
        bridge: br-ex
        port: bond1
        interfaces:
          - eth4
          - eth5
        bond_updelay: 100
        bond_downdelay: 100
        state: present
      args:
        other_config:
          bond-detect-mode: miimon
          bond-miimon-interval: '"100"'
    - name: Create an active LACP bond using DPDK interfaces
      openvswitch.openvswitch.openvswitch_bond:
        bridge: br-provider
        port: dpdkbond
        interfaces:
          - "0000:04:00.0"
          - "0000:04:00.1"
        lacp: active
        set:
          - "interface 0000:04:00.0 type=dpdk options:dpdk-devargs=0000:04:00.0"
          - "interface 0000:04:00.1 type=dpdk options:dpdk-devargs=0000:04:00.1"
        state: present




Status
------


Authors
~~~~~~~

- James Denton (@busterswt)
