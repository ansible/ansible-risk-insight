# Rule definitions

You can define each custom rule in a single Python class file.

Each rule definition should have the following parts:

[required]
- `rule_id` is a unique identifier among rules
- `description` explains what the rule checks for.
- `enabled` determines whether the rule is used or not.
- `name` is a short description of the rule.

[optional]
- `tags` specifies one or more tags for including or excluding the rule.
- `severity` represents the risk impact if the rule condition is matched.
- `precedence` is used to control the order of execution.


## match and process methods

Each rule definition should also have `match` and `process` methods.

### match
`match` takes the `context` information and returns True if the rule should check this target.

When ARI is scanning a playbook, ARI updates the context by focusing on each runnable target such as Playbook, Role and Task.

The current object of the context can be accessed by `ctx.current`, so if the rule is only for tasks, you can define a `match` method like the following.


```python
from dataclasses import dataclass

from ansible_risk_insight.models import (
    AnsibleRunContext,
    RunTargetType,
    Rule,
    RuleResult,
    Severity,
)

class SampleRule(Rule):
    rule_id: str = "Sample101"
    description: str = "echo task block"
    enabled: bool = True
    name: str = "EchoTaskContent"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    
    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task
```

### process
`process` also takes the context, but it returns a RuleResult object.

Normally, you can make this result object just by preparing the following things.

- `detail` is the data shown in the result (console output / UI)
- `verdict` indicates the rule is matched or not.
- file information of the task or role
- rule metadata

In the example below, the sample rule gets the task content.
This rule also compute the verdict by checking the annotation.  
Then, the rule puts the data into detail.

 
```python
    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = True
        detail = {}
        task_block = task.content.yaml()
        detail["task_block"] = task_block
        
        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())

```

## Mutating rule
`process` also can mutate the task content.

You can use the following methods to change task content.
- set_module_name(module_name)
- replace_key(old_key, new_key)
- replace_value(old_value, new_value)
- remove_key(key)
- set_new_module_arg_key(key, value)
- remove_module_arg_key(key)
- replace_module_arg_key(old_key, new_key)
- replace_module_arg_value(key, old_value, new_value)

This is an example of changing a task option by the mutating rule.

```python
    def process(self, ctx: AnsibleRunContext):
        task = ctx.current
        detail = {}

        verdict = True

        old_value = "foo"
        new_value = "bar"
        content = task.content # get a task content from context
        content.replace_value(old_value, new_value) # replace value in the task option
        mutated_yaml = content.yaml() # convert to yaml format
        detail["mutated_yaml"] = mutated_yaml # put mutated yaml into rule result

        return RuleResult(detail=detail, verdict=verdict, file=task.file_info(), rule=self.get_metadata())

```

## Using annotation
ARI provides various useful annotations.  
You can write your own rules easily by using those annotations. 
The available annotations are shown in [here](./annotation.md).

You can retrieve an annotation by defining annotation `key` to `get_annotation` method.

This example rule gets data from the task annotation.  

```python
    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        detail = {}
        verdict = False
        undefined_vars = task.get_annotation(key="variable.undefined_vars") # getting undefined variables

        detail["undefined_vars"] = undefined_vars
        
        if undefined_vars:
            verdict = True
        
        return RuleResult(detail=detail, verdict=verdict, file=task.file_info(), rule=self.get_metadata())

```

### Using the results of other rules

Rule can use the results of other rules.

To pass the results on to other rules, you can set an annotation by using `set_annotation`.
And you can use `get_annotation` to use the results of other rules.

This is an example of setting an annotation in one rule and use the annotation from another rule.

In such cases, the order of rule execution is important. 
You can specify the order by setting `precedence` in the rule definition.

- This rule sets `applied_changes` annotation and passes the mutation details.
```python
    def process(self, ctx: AnsibleRunContext):
        task = ctx.current
        detail = {}

        verdict = True
        changes = {}

        old_value = "foo"
        new_value = "bar"

        content = task.content 
        content.replace_value(old_value, new_value)
        changes = {"before": old_value,  "after": new_value}
        mutated_yaml = content.yaml() 

        detail["mutated_yaml"] = mutated_yaml 
        detail["applied_changes"] = changes
        applied_changes = {"description": self.description, "applied_changes": changes}
        task.set_annotation("applied_changes", applied_changes, rule_id=self.rule_id) # setting annotation here

        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
```

- This another rule retrieves the annotations and summarize the changes.

Also, since this rule should be executed last, we define a large number for the precedence.

```python
@dataclass
class PostProcessingRule(Rule):
    rule_id: str = "CR102"
    description: str = "Export mutated yaml"
    enabled: bool = True
    name: str = "GetMutatedYaml"
    version: str = "v0.0.1"
    severity: Severity = Severity.NONE
    precedence: int = 20

    def match(self, ctx: AnsibleRunContext) -> bool:
        return ctx.current.type == RunTargetType.Task

    def process(self, ctx: AnsibleRunContext):
        task = ctx.current

        verdict = True
        detail = {}
        mutated_yaml = task.content.yaml()
        detail["mutated_yaml"] = mutated_yaml
        # detail
        _detail["mutation_result"] = {
            "changes": task.get_annotation(key="applied_changes"), # getting annotation
        }
        detail["detail"] = _detail
        return RuleResult(verdict=verdict, detail=detail, file=task.file_info(), rule=self.get_metadata())
```

