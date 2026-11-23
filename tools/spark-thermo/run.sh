#!/bin/bash
# run.sh <logname> <command...>: runs one job with its log in $THERMO_BASE/logs/<logname>.log.
# Refuses to start if $THERMO_BASE/STOP exists (written by thermo.py after a kill).
B=${THERMO_BASE:-$HOME/thermo-work}
[ -f "$B/env.sh" ] && source "$B/env.sh"
mkdir -p "$B/logs"
name=$1; shift
log=$B/logs/$name.log
if [ -f "$B/STOP" ]; then echo "=== $(date "+%F %T") STOP present, not starting: $*" >> "$log"; exit 99; fi
echo "=== $(date "+%F %T") start (GOV_DUTY=${GOV_DUTY:-0.5}): $*" >> "$log"
"$@" >> "$log" 2>&1
rc=$?
echo "=== $(date "+%F %T") end rc=$rc: $*" >> "$log"
echo "$(date "+%F %T") $name rc=$rc: $*" >> "$B/logs/jobs.log"
exit $rc
