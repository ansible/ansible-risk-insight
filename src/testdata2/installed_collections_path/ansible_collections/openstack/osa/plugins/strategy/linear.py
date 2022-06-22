# Copyright 2016, Rackspace US, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# (c) 2016, Kevin Carter <kevin.carter@rackspace.com>

import copy
import importlib.util
import os

def load_module(name, path):

    module_spec = importlib.util.spec_from_file_location(
        name, path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module

# NOTICE(cloudnull): The connection plugin imported using the full path to the
#                    file because the linear strategy plugin is not importable.
import ansible.plugins.strategy as strategy
LINEAR = load_module(
    'ssh',
    os.path.join(os.path.dirname(strategy.__file__), 'linear.py')
)

# NOTICE(jmccrory): MAGIC_VARIABLE_MAPPING is imported so that additional
#                   container specific variables can be made available to
#                   the connection plugin.
#                   In Ansible 2.5 the magic variable mapping has been moved,
#                   but updating it directly is no longer necessary. The
#                   variables can be made available through being defined in
#                   the connection plugin's docstring and this can eventually
#                   be removed.
try:
    from ansible.playbook.play_context import MAGIC_VARIABLE_MAPPING
    MAGIC_VARIABLE_MAPPING.update({
        'physical_host': ('physical_host',),
        'container_name': ('inventory_hostname',),
        'container_tech': ('container_tech',),
        'container_user': ('container_user',),
    })
except ImportError:
    pass

class StrategyModule(LINEAR.StrategyModule):
    """Notes about this strategy.

    When this strategy encounters a task with a "when" or "register" stanza it
    will collect results immediately essentially forming a block. If the task
    does not have a "when" or "register" stanza the results will be collected
    after all tasks have been queued.

    To improve execution speed if a task has a "when" conditional attached to
    it the conditional will be rendered before queuing the task and should the
    conditional evaluate to True the task will be queued. To ensure the correct
    execution of playbooks this optimisation will only be used if there are no
    lookups used with the task which is to guarantee proper task execution.

    Container context will be added to the ``playbook_context`` which is used
    to further optimise connectivity by only ever SSH'ing into a given host
    machine instead of attempting an SSH connection into a container.
    """

    @staticmethod
    def _check_when(host, task, templar, task_vars):
        """Evaluate if conditionals are to be run.

        This will error on the side of caution:
            * If a conditional is detected to be valid the method will return
              True.
            * If there's ever an issue with the templated conditional the
              method will also return True.
            * If the task has a detected "with" the method will return True.

        :param host: object
        :param task: object
        :param templar: object
        :param task_vars: dict
        """
        try:
            if not task.when or (task.when and task.register):
                return True

            _ds = getattr(task, '_ds', dict())
            if any([i for i in _ds.keys() if i.startswith('with')]):
                return True

            conditional = task.evaluate_conditional(templar, task_vars)
            if not conditional:
                LINEAR.display.verbose(
                    u'Task "%s" has been omitted from the job because the'
                    u' conditional "%s" was evaluated as "%s"'
                    % (task.name, task.when, conditional),
                    host=host,
                    caplevel=0
                )
                return False
        except Exception:
            return True
        else:
            return True

    def _queue_task(self, host, task, task_vars, play_context):
        """Queue a task to be sent to the worker.

        Set a host variable, 'physical_host_addrs', containing a dictionary of
        each physical host and its 'ansible_host' variable.

        """
        templar = LINEAR.Templar(loader=self._loader, variables=task_vars)
        if not self._check_when(host, task, templar, task_vars):
            return

        pha = task_vars['physical_host_addrs'] = dict()
        physical_host_items = [task_vars.get('physical_host')]
        if task.delegate_to:
            # For delegated tasks, we also need the information from the delegated hosts
            for delegated_host in task_vars.get('ansible_delegated_vars', dict()).keys():
                LINEAR.display.verbose(
                    u'Task is delegated to %s.' % delegated_host,
                    host=host,
                    caplevel=0
                )
                delegated_host_info = self._inventory.get_host(u'%s' % delegated_host)
                # This checks if we are delegating to a host which does not exist
                # in the inventory (possibly using its IP address)
                if delegated_host_info is None:
                    task_vars['container_name'] = None
                    continue
                physical_host_vars = delegated_host_info.get_vars()
                physical_host_templar = LINEAR.Templar(loader=self._loader,
                                                       variables=physical_host_vars)
                delegated_physical_host = physical_host_templar.template(
                    physical_host_vars.get('physical_host'))
                if delegated_physical_host:
                    physical_host_items.append(delegated_physical_host)
                    LINEAR.display.verbose(
                        u'Task is delegated to %s. Adding its physical host %s'
                        % (delegated_host, delegated_physical_host),
                        host=host,
                        caplevel=0
                    )
        for physical_host_item in physical_host_items:
            ph = self._inventory.get_host(physical_host_item)
            if ph:
                LINEAR.display.verbose(
                    u'The "physical_host" variable of "%s" has been found to'
                    u' have a corresponding host entry in inventory.'
                    % physical_host_item,
                    host=host,
                    caplevel=0
                )
                physical_host_vars = ph.get_vars()
                for item in ['ansible_host', 'container_address', 'address']:
                    addr = physical_host_vars.get(item)
                    if addr:
                        LINEAR.display.verbose(
                            u'The "physical_host" variable of "%s" terminates'
                            u' at "%s" using the host variable "%s".' % (
                                physical_host_item,
                                addr,
                                item
                            ),
                            host=host,
                            caplevel=0
                        )
                        pha[ph.name] = addr
                        break

        return super(StrategyModule, self)._queue_task(
            host,
            task,
            task_vars,
            play_context
        )
