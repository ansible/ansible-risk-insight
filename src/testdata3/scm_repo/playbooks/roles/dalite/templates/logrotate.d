/var/log/dalite/student.log {
        daily
        missingok
        ifempty
        dateext
        create 0666 dalite dalite
        rotate 3653
        postrotate
            {{ DALITE_TARSNAP_BACKUP_SCRIPT }} > /dev/null 2>&1
        endscript
}
