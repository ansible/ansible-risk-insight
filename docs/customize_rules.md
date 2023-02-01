# Rule definitions

You can define each custom rule in a single Python class file.

Each rule definition should have the following parts:

[required]
- `rule_id` is a unique identifier among rules
- `description` explains what the rule checks for.
- `enabled` determines whether the rule is used or not.

[optional]
- `tags` specifies one or more tags for including or excluding the rule.
- `severity` represents the risk impact if the rule condition is matched.
- `result_type` specifies the result type class instead of the default one.


## match and check methods

Each rule definition should also have `match` and `check` methods:

`match` takes the `context` information and returns True if the rule should check this target.

When ARI is scanning a playbook, ARI updates the context by focusing on each runnable target such as Playbook, Role and Task.

The current object of the context can be accessed by `ctx.current`, so if the rule is only for tasks, you can define a `match` method like the following.


```python
from dataclasses import dataclass
from ansible_risk_insight.models import AnsibleRunContext, RunTargetType, ExecutableType as ActionType
from ansible_risk_insight.rules.base import Rule

@dataclass
class NonBuiltinUseRule(Rule):
    rule_id: str = "R110"
    description: str = "Non-builtin module is used"
    enabled: bool = True
    
    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task
```

`check` also takes the context, but it returns a RuleResult object.

Normally, you can make this result object just by preparing the following 3 things.

- `result` represents if the target (e.g. task) met with the rule condition or not
- `detail` is the data shown in the result (console output / UI)
- target itself (e.g. task or role)

Then you can call `self.create_result()` like below to create result object.

In the example below, the rule condition is composed of 3 conditions - 1. the task invokes a module (not import/include), 2. the module was resolved and 3. the module is not "ansbile.builtin" one.

A task has a FQCN of the resolved module as `task.resovled_name`, so the information is included in `detail`.

```python


    def check(self, ctx: AnsibleRunContext):
        task = ctx.current

        result = (
            task.action_type == ActionType.MODULE_TYPE and 
            task.resolved_action and
            not task.resolved_action.startswith("ansible.builtin.")
        )

        detail = {
            "fqcn": task.resolved_name,
        }

        rule_result = self.create_result(result=result, detail=detail, task=task)
        return rule_result
```


## Define custom rule result type

To customize the output format of the result data, you can define your own rule result class.

A custom rule result class should have a method `print`:

`print` is a method for formatting the output string of the rule result.

It can access rule properties by `self._rule`, and it has detail as `self.detail`.

Also it has the original file information of the task such as file name with `self.file` and line number of the task block with `self.lines`.

To enable your own RuleResult, you can specify the class name in the `result_type` field in rules like below.


```python
from dataclasses import dataclass
from ansible_risk_insight.rules.base import RuleResult


@dataclass
class NonBuiltinUseRuleResult(RuleResult):
    def print(self):
        output = f"ruleID={self._rule.rule_id}, \
            description={self._rule.description}, \
            result={self.result}, \
            file={self.file}, \
            lines={self.lines}, \
            detail={self.detail}\n"
        return output


@dataclass
class NonBuiltinUseRule(Rule):
    rule_id: str = "R110"
    description: str = "Non-builtin module is used"
    enabled: bool = True
    risk_type: type = NonBuiltinUseRuleResult

```

