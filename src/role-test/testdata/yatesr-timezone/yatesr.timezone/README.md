Role Name
========

timezone

Role Variables
--------------

```

# Default timezone.  Must be a valid tz database time zone.
timezone: UTC

```

Example Playbook
-------------------------

```

---
- hosts: all
  roles:
  - yatesr.timezone

  vars:
   timezone: America/New_York

```

License
-------

Apache 2.0

Author Information
------------------

Ryan Yates
