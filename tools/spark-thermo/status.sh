#!/bin/bash
# Local: temperature summary of the last N samples, watchdog events, STOP, RAM and the tail of one job log.
# Usage: SPARK_HOST=user@host [THERMO_BASE_REMOTE=~/thermo-work] status.sh [N=24] [logname]
H=${SPARK_HOST:?set SPARK_HOST=user@host}
R=${THERMO_BASE_REMOTE:-'~/thermo-work'}
N=${1:-24}; L=${2:-}
ssh -o BatchMode=yes -o ConnectTimeout=20 "$H" "
tail -n $N $R/logs/temp.csv | awk -F, '{n++; p+=\$3; if(\$9>z)z=\$9; if(\$3>pm)pm=\$3; if(\$2>g)g=\$2} END {printf \"last %d: zone max %.1f, gpu max %d, power mean %.1f max %.1f\n\", n, z, g, p/n, pm}'
awk -F, 'NR>1 {if(\$9>z)z=\$9; if(\$3>pm)pm=\$3} END {printf \"all: zone max %.1f, power max %.1f\n\", z, pm}' $R/logs/temp.csv
grep -v started $R/logs/watchdog.log | tail -n 3
ls $R/STOP 2>/dev/null && cat $R/STOP
free -g | sed -n 2p
[ -n '$L' ] && tail -c 1500 $R/logs/$L.log 2>/dev/null | tr '\r' '\n' | grep -v '^\s*$' | tail -n 6
date +%T"
