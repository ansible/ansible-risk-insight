## Annotation

ARI provides some default annotations.  
Annotations are attached to each node so that it can be retrieved from each context.
From your rule, you can get an annotation by defining annotation `key` to `get_annotation` method.
```python
def process(self, ctx: AnsibleRunContext):
    task = ctx.current
    # getting resolved fqcn data from annotation
    resolved_fqcn = task.get_annotation(key="module.resolved_fqcn")
```

The default annotations are shown in the tables.

1. annotations about module

|  key  |   value	|
|---	|---	|
| module.wrong_module_name  	|   non-existing module name	|
| module.suggested_fqcn   	|   inferred FQCN 	|
| module.resolved_fqcn  	|   resolved FQCN from dependency list	|
| module.not_exist  	| true if non-existing module name is used 	|
| module.correct_fqcn  	|   best guess for FQCN	|
| module.need_correction 	|  true if module name should be replaced with correct_fqcn 	|
| module.suggested_dependency 	|   inferred dependencies	|



2. annotations about module argument key

|  key 	|   value	|
|---	|---	|
|  module.wrong_arg_keys 	|   non-existing arg keys for the module	|
|  module.available_arg_keys 	|   supported arg keys for the module	|
|  module.required_arg_keys 	|  required arg keys for the module	|
|  module.missing_required_arg_keys 	|   missing required arg keys for the module	|
|  module.available_args 	|   detail information for the module (derived via ansible-doc)	|
| module.used_alias_and_real_keys  	|   arg keys using alias	|


3. annotations about module argument value

|  key 	|  value 	|
|---	|---	|
|  module.wrong_arg_values 	|   arg values using wrong format, expected format is also included|
|  module.undefined_values 	|   undefined arg values	|
|  module.unknown_type_values 	|  parameterized arg values (= cannot determine the value type) 	|

 

4. annotations about variable

|  key 	|  value 	|
|---	|---	|
|  variable.undefined_vars 	|   undefined variables used in the task	|
|  variable.unnecessary_loop_vars 	|   unnecessary loop vars (e.g. “item”) used outside of the loop	|
|  variable.unknown_name_vars 	|   undefined var & the var name is different from the key name	|
