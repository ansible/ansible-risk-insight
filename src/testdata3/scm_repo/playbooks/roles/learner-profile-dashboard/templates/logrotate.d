/var/log/lpd/debug.log {
        daily
        missingok
        ifempty
        dateext
        create 0666 lpd lpd
        rotate 3653
        postrotate
            {{ LPD_TARSNAP_BACKUP_SCRIPT }} > /dev/null 2>&1
        endscript
}
