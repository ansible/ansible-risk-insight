Backup Swift Container to Tarsnap
=================================

A role that backs up swift container to Tarsnap, for now only a single container per VM can be backed up, but that
can be implemented easily.

New backups will be saved to Tarsnap hourly, and will not be deleted by this role, this is by design, we don't
want keys that allow deletion anywhere near production VM's.

For configurable settings please see: `defaults/main.yml`.
