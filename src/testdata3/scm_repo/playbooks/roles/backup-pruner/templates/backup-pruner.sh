#jinja2: trim_blocks:False
#!/bin/bash
# This script runs all of the backup pruners in parallel, returning the output
# of only the failing pruners.
# Check {{ BACKUP_PRUNER_JOB_LOG }} for a summary of the most recent pruner run.
# Check the {{ BACKUP_PRUNER_LOG_DIR }} for the full log of each pruning task.
set -e

jobs='{% for item in BACKUP_PRUNER_TARSNAPPER_JOBS %}
{{ item.name }}{% endfor %}'

# Buffer the output of each pruner per-task; if the pruner fails (returns a
# non-zero exit status), forward along the output to GNU Parallel, which will
# then simply forward the output along to cron.
# The `test ${PIPESTATUS[0]} -eq 0` part is checking the return status of the
# pruner script; this is necessary because we don't care about the return
# status of `tee`, which will always be 0.
task='output=$(/usr/local/sbin/tarsnap-{}.sh expire 2>&1 | tee -a {{ BACKUP_PRUNER_LOG_DIR }}/{}.log ; test ${PIPESTATUS[0]} -eq 0) || (echo "$output" && exit 1)'
# Cron will send email if there is any stdout or stderr output regardless of the
# response code, so by only including output for failed tasks in the output, an
# email will only be sent out if and only if one or more backup pruners failed.
echo "$jobs" | tail -n +2 | parallel {% if BACKUP_PRUNER_JOB_NOSWAP %}--noswap{% endif %} \
  --no-notice \
  -j{{ BACKUP_PRUNER_JOB_PARALLELISM }} \
  --retries {{ BACKUP_PRUNER_JOB_RETRIES }} \
  --nice {{ BACKUP_PRUNER_JOB_NICENESS }} \
  --joblog {{ BACKUP_PRUNER_JOB_LOG }} $task
status=$?

if [ $status -eq 0 ]
then
  curl -s -S {{ BACKUP_PRUNER_SNITCH }} > /dev/null
fi

exit $status
