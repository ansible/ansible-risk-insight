# Copyright 2017, Rackspace US, Inc.
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

import itertools

from .linear import StrategyModule as LinearStrategyModule


class StrategyModule(LinearStrategyModule):
    def _queue_task(self, host, task, task_vars, play_context):
        """Wipe the notification system and return for config tasks."""
        skip_handlers = task_vars.get('skip_handlers', True)
        if skip_handlers:
            task.notify = None
        skip_tags = task_vars.get('skip_tags')
        if isinstance(skip_tags, str):
            skip_tags = [skip_tags]
        if skip_tags:
            if not hasattr(skip_tags, '__iter__'):
                skip_tags = (skip_tags,)
        else:
            skip_tags = ()
        if any([True for (i, j) in itertools.product(skip_tags, task.tags)
               if i in j]):
            return
        else:
            return super(StrategyModule, self)._queue_task(
                host,
                task,
                task_vars,
                play_context
            )
