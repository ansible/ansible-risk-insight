=======
Filters
=======

deprecated
~~~~~~~~~~
This filter will return the old_var value, if defined, along with a
deprecation warning that will inform the user that the old variable
should no longer be used.

In order to use this filter the old and new variable names must be provided
to the filter as a string which is used to render the warning message. The
removed_in option is used to give a date or release name where the old
option will be removed. Optionally, if fatal is set to True, the filter
will raise an exception if the old variable is used.

.. code-block:: yaml

   old_var: "old value"
   old_var_name: "old_var"
   new_var_name: "new_var"
   removed_in: "Next release"
   fatal_deprecations: false

   {{ new_var | deprecated(old_var,
                                  old_var_name,
                                  new_var_name,
                                  removed_in,
                                  fatal_deprecations) }}
   # WARNING => Deprecated Option provided: Deprecated variable:
   # "old_var", Removal timeframe: "Next release", Future usage:
   # "new_var"
   # => "old value"

splitlines
~~~~~~~~~~
This filter will return of list from a string with line breaks.

.. code-block:: yaml

    string_with_line_breaks: |
      a string
      with
      line
      breaks

    {{ string_with_line_breaks | splitlines }}
    # => [ "a string", "with", "line", "breaks" ]

string_2_int
~~~~~~~~~~~~
This filter will hash a given string, convert it to a base36 int, and return
the modulo of 10240.

.. code-block::

   {{ 'openstack-ansible' | string_2_int }}
   # => 3587
