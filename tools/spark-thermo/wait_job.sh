#!/bin/bash
# Local: wait (at most MAX minutes) until a job ends on the remote machine (jobs.log grows) or STOP appears.
# Usage: SPARK_HOST=user@host [THERMO_BASE_REMOTE=~/thermo-work] wait_job.sh [MAX=30]
H=${SPARK_HOST:?set SPARK_HOST=user@host}
R=${THERMO_BASE_REMOTE:-'~/thermo-work'}
MAX=${1:-30}
q() { ssh -o BatchMode=yes -o ConnectTimeout=20 "$H" "echo \$(cat $R/logs/jobs.log 2>/dev/null | wc -l) \$(ls $R/STOP 2>/dev/null | wc -l)" 2>/dev/null; }
n0=$(q); n0=${n0%% *}; end=$(( $(date +%s) + MAX * 60 ))
while [ "$(date +%s)" -lt $end ]; do
  sleep 30; cur=$(q); [ -z "$cur" ] && continue
  set -- $cur
  [ "$1" != "$n0" ] && { echo "job ended"; ssh "$H" "tail -n 1 $R/logs/jobs.log"; exit 0; }
  [ "$2" != 0 ] && { echo "STOP present"; exit 2; }
done
echo "still running after $MAX min"; exit 1
